import os, re
import sys
from flask import (Flask, render_template, session, redirect, url_for, escape,
    request, current_app as app)
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
from subscribie.forms import ItemsForm
from subscribie import (current_app)
from flask import Blueprint
import json
import uuid

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
    session['plan'] = str(request.args.get('plan'))
    form = ItemsForm()
    return render_template('start-building.html', form=form)



@builder.route('/start-building', methods=['POST'])
def save_items():
    payload = {}
    form = ItemsForm()
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
        item['sell_price'] = getItem(form.sell_price.data, index) or 0
        item['sell_price'] = int(item['sell_price'] * 100)
        item['monthly_price'] = getItem(form.monthly_price.data, index) or 0
        item['monthly_price'] = int(item['monthly_price'] * 100)
        item['selling_points'] = getItem(form.selling_points.data, index)
        item['subscription_terms'] = {'minimum_term_months': 12}
        item['primary_colour'] = "#e73b1a"
        # Item requirements
        item['requirements'] = {};
        item['requirements']['instant_payment'] = getItem(form.instant_payment.data, index)
        item['requirements']['subscription'] = getItem(form.subscription.data, index)
        item['requirements']['note_to_seller_required'] = False
        # Image storage
        f = getItem(form.image.data, index)
        if f:
            filename = secure_filename(f.filename)
            src = os.path.join(getConfig('UPLOADED_IMAGES_DEST'), filename)
            f.save(src)
            item['primary_icon'] = {'src': '/static/' + filename, 'type': ''}
        else:
            item['primary_icon'] = {'src':False, 'type': False}
        print(item)
        items.append(item)
        payload['items'] = items

    # Payment provider information
    payload['payment_providers'] = {}
    payload['payment_providers']['stripe'] = {}
    payload['payment_providers']['gocardless'] = {}
    payload['payment_providers']['paypal'] = {}

    # Paypal
    payload['payment_providers']['paypal']['sepa_direct_supported'] = False
    payload['payment_providers']['paypal']['subscription_supported'] = True
    payload['payment_providers']['paypal']['instant_payment_supported'] = True
    payload['payment_providers']['paypal']['variable_payments_supported'] = False

    # Stripe
    payload['payment_providers']['stripe']['sepa_direct_supported'] = True
    payload['payment_providers']['stripe']['subscription_supported'] = True
    payload['payment_providers']['stripe']['instant_payment_supported'] = True
    payload['payment_providers']['stripe']['variable_payments_supported'] = True
    payload['payment_providers']['stripe']['publishable_key'] = ''
    payload['payment_providers']['stripe']['secret_key'] = ''

    # Gocardless
    payload['payment_providers']['gocardless']['sepa_direct_supported'] = True
    payload['payment_providers']['gocardless']['subscription_supported'] = True
    payload['payment_providers']['gocardless']['instant_payment_supported'] = True
    payload['payment_providers']['gocardless']['variable_payments_supported'] = True
    payload['payment_providers']['gocardless']['access_token'] = ''
    payload['payment_providers']['gocardless']['environment'] = ''

    # Integrations                                                               
    payload['integrations'] = {}                                              
    payload['integrations']['google_tag_manager'] = {}                        
    payload['integrations']['google_tag_manager']['active'] = False           
    payload['integrations']['google_tag_manager']['container_id'] = ''

    # Tawk                                                                       
    payload['integrations']['tawk'] = {}                                      
    payload['integrations']['tawk']['active'] = False                         
    payload['integrations']['tawk']['property_id'] = ''

    subdomain = create_subdomain_string(payload)
    session['site-url'] = 'https://' + subdomain.lower() + '.subscriby.shop'

    # Save to json
    output = json.dumps(payload)
    with open(subdomain + '.json', 'w') as fp:
        fp.write(json.dumps(payload))
    deployJamla(subdomain + '.json')
    # Redirect to activation page
    url = 'https://' + request.host + '/activate/' + subdomain
    return redirect(url) 

@builder.route('/activate/<sitename>')
def choose_package(sitename=None):
    jamla = get_jamla()
    items = []                                                               
    for item in jamla['items']:                                              
        try:                                                                 
            if item['archived'] is not True:                                 
                items.append(item)                                           
        except KeyError:                                                     
            items.append(item) # if key is absent, assume not archived
    jamla['items'] = items
    try:
        plan = session['plan']
        if session['plan'] and is_valid_sku(plan):
           return redirect(url_for('views.new_customer', plan=plan))
    except Exception:
        pass
    return render_template('select-package.html', jamla=jamla)

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

def is_valid_sku(sku):
    for item in jamla['items']:
        if item['sku'] == sku:
            return True
    return False


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


def getItem(container, i, default=None):
    try:
        return container[i]
    except IndexError:
        return default


# Subscribers
journey_complete.connect(journey_complete_subscriber)
