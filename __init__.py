import os, re
import sys
from flask import (Flask, render_template, session, redirect, url_for, escape,
    request, flash, current_app as app)
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import (StringField, FloatField, FieldList, FileField, validators,
    BooleanField, TextField)
from wtforms.validators import DataRequired
from flask_mail import Mail, Message
import yaml
from yaml import load, dump
import requests
from base64 import urlsafe_b64encode
from contextlib import contextmanager
from subscribie.signals import journey_complete
from .forms import SignupForm
from subscribie.forms import LoginForm
from subscribie import (current_app, Item)
from flask import Blueprint
import json
import uuid
import sqlite3

builder = Blueprint('builder', __name__, template_folder='templates')

def getConfig(name=None):
  if name is None:
    allConfigs = {}
    for key,value in enumerate(os.environ):
      allConfigs[key] = value;
    for key,value in enumerate(app.config):
      allConfigs[key] = value
    return allConfigs
  try: #Default get from os environment
    print("NOTICE: Attempting to find {} in os environ".format(name))
    return os.environ[name]
  except KeyError:
    pass
  try: # Fallback get from app config
    print("NOTICE: Attempting to find {} in app config".format(name))
    return app.config[name]
  except KeyError:
    pass

  print("NOTICE: Could not loate value for config: {}".format(name))
  return False

def get_couchdb_url():
  couch_con_url = ''.join([getConfig('COUCHDB_SCHEME'), 
                              getConfig('COUCHDB_USER'), ':',
                              getConfig('COUCHDB_PASSWORD'), '@',
                              getConfig('COUCHDB_IP'), ':',
                              str(getConfig('COUCHDB_PORT')), '/',
                              getConfig('COUCHDB_DBNAME')])
  return couch_con_url

def getLatestCouchDBRevision(host, docid):
  req = requests.get(host + '/' + docid)
  resp = json.loads(req.text)
  if '_rev' in resp:
    revisionId = resp['_rev']
  else:
    revisionId = None
  return revisionId


@builder.route('/start-building', methods=['GET'])
def start_building():
    form = SignupForm()
    return render_template('start-building.html', form=form)


@builder.route('/start-building', methods=['POST'])
def save_items():
    payload = {}
    form = SignupForm()
    payload['version'] = 1
    payload['modules_path'] = '../../../'
    payload['modules'] = [
      {'name': 'module_seo_page_title', 
       'src': 'https://github.com/Subscribie/module-seo-page-title.git'
      },
      {'name': 'module_iframe_embed',
       'src': 'https://github.com/Subscribie/module-iframe-embed.git'
      },
      {'name': 'module_style_shop',
       'src': 'https://github.com/Subscribie/module-style-shop.git'
      },
      {'name': 'module_pages',
       'src': 'https://github.com/Subscribie/module-pages.git'
      }
    ]
    payload['users'] = [form.email.data]
    session['email'] = form.email.data
    payload['password'] = form.password.data
    company_name = form.company_name.data
    payload['company'] = {'name':company_name, 'logo':'', 'start_image':''}
    payload['theme'] = { 'name': 'jesmond', 'static_folder': './static/' }

    # Custom styles prepare as empty
    payload['theme']['options']= {}
    payload['theme']['options']['styles'] = []

    # Pages as empty array
    payload['pages'] = []

    items = []
    for index, item in enumerate(form.title.data):
        item = {}
        item['uuid'] = str(uuid.uuid4())
        item['title'] = getItem(form.title.data, index)
        item['sku'] = getItem(form.title.data, index)
        if getItem(form.sell_price.data, index) is None:
            item['sell_price'] = 0
        else:
            item['sell_price'] = int(getItem(form.sell_price.data, index)) * 100
        if getItem(form.interval_amount.data, index) is None:
            item['interval_amount'] = 0
        else:
            item['interval_amount'] = getItem(form.interval_amount.data, index) * 100
        item['interval_unit'] = getItem(form.interval_unit.data, index)
        item['selling_points'] = getItem(form.selling_points.data, index)
        item['subscription_terms'] = {'minimum_term_months': 12}
        item['primary_colour'] = "#e73b1a"
        # Item requirements
        item['requirements'] = {};
        item['requirements']['instant_payment'] = getItem(form.instant_payment.data, index)
        item['requirements']['subscription'] = getItem(form.subscription.data, index)
        item['requirements']['note_to_seller_required'] = False
        item['primary_icon'] = {'src':False, 'type': False}
        print(item)
        items.append(item)
        payload['items'] = items

    subdomain = create_subdomain_string(payload)
    session['site-url'] = 'https://' + subdomain.lower() + '.subscriby.shop'

    # Save to json
    output = json.dumps(payload)
    with open(subdomain + '.json', 'w') as fp:
        fp.write(json.dumps(payload))
    deployJamla(subdomain + '.json')
    # Redirect to activation page
    url = 'https://' + request.host + '/activate/' + subdomain

    # Store new site in builder_sites table to allow logging in from subscibie site
    con = sqlite3.connect(app.config["DB_FULL_PATH"])
    cur = con.cursor()
    query = "INSERT INTO builder_sites (site_url, email) VALUES (?, ?)"
    con.execute(query, (session["site-url"], session['email'].lower()))
    con.commit()


    return redirect(url) 

@builder.route('/activate/<sitename>')
def choose_package(sitename=None):
    items = Item.query.filter_by(archived=0)
    return render_template('select-package.html', items=items)

def journey_complete_subscriber(sender, **kw):
    print("Journery Complete! Send an email or something..")
    try:
        email = kw['email']
        sender = "hello@example.co.uk"
        login_url = session['login-url']
        msg  = Message(subject="Subscription Website Activated",
                       body=login_url,
                       sender=sender,
                       recipients=[email])
        # Load builder module env
        mail = Mail(current_app)
        mail.send(msg)
    except Exception:
        print ("Error sending journey_complete_subscriber email")
        pass


@builder.route('/sendJamla')
def deployJamla(filename):
    url = getConfig('JAMLA_DEPLOY_URL')
    with open(filename) as fp:
        payload = json.loads(fp.read())
        r = requests.post(url, json=payload)
        session['login-url'] = r.text
    return "Sent jamla file for deployment"

def create_subdomain_string(jamla=None):
    if jamla is None:
        subdomain = urlsafe_b64encode(os.urandom(5)).replace('=', '')
    else:
        subdomain = re.sub(r'\W+', '', jamla['company']['name'])
    return subdomain

@builder.route('/shop-owner-login/', methods=["GET", "POST"])
def show_owner_login():
    """Locate and redirect shop owner to their shop url

    Shops are hosted on their own instance, with their own database
    so we must direct them to their shop, by:

    - Searching for their shop url, via email
    - Redirect user to their shop's login page
    """
    if request.method == "POST":
        email = request.form['email'].lower()
        con = sqlite3.connect(app.config["DB_FULL_PATH"])
        cur = con.cursor()
        query = "SELECT site_url FROM builder_sites WHERE email = ?"
        cur.execute(query, (email,))
        result = cur.fetchone()
        if result is None:
            flash("Site not found, please use the email used during sign-up")
            return redirect(url_for('builder.show_owner_login'))
        else:
            # Redirect user to their shop url
            site_url = result[0]
            destination = site_url + "/auth/login"
            return redirect(destination)
            
    if request.method == "GET":
        form = LoginForm()
        return render_template("login.html", form=form)

def getItem(container, i, default=None):
    try:
        return container[i]
    except IndexError:
        return default


# Subscribers
journey_complete.connect(journey_complete_subscriber)
