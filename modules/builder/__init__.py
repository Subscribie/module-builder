import os, re
import sys
sys.path.append('../../Indigo/hedgehog/hedgehog/')
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
from hedgehog import (app, Jamla, journey_complete, generate_login_url, 
                      ItemsForm)



# Load Jamla
jamlaApp = Jamla()
jamla = jamlaApp.load(app.config['JAMLA_PATH'])

# Load builder module env
curDir = os.path.dirname(os.path.realpath(__file__))
app.config.from_pyfile('/'.join([curDir, '.env']))
mail = Mail(app)


@app.route('/start-building', methods=['GET'])
def start_building():
    session['plan'] = str(request.args.get('plan'))
    form = ItemsForm()
    return render_template('start-building.html', jamla=jamla, form=form)



@app.route('/start-building', methods=['POST'])
def save_items():
    draftJamla = {}
    form = ItemsForm()
    draftJamla['version'] = 1
    draftJamla['modules_path'] = '../../../'
    draftJamla['users'] = [form.email.data]
    session['email'] = form.email.data
    company_name = form.company_name.data
    draftJamla['company'] = {'name':company_name, 'logo':'', 'start_image':''}
    draftJamla['theme'] = { 'name': 'jesmond' }
    items = []
    for index, item in enumerate(form.title.data):
        item = {}
        item['title'] = getItem(form.title.data, index)
        item['sku'] = getItem(form.title.data, index)
        item['sell_price'] = getItem(form.sell_price.data, index) or 0
        item['sell_price'] = int(item['sell_price'] * 100)
        item['monthly_price'] = getItem(form.monthly_price.data, index) or 0
        item['monthly_price'] = int(item['monthly_price'] * 100)
        item['selling_points'] = getItem(form.selling_points.data, index)
        item['subscription_terms'] = {'minimum_term_months': 12}
        item['primary_colour'] = "#e73b1a"
        item['icons'] = [{'src':'images/item3148.png',
                          'size':'48x48', 'type':'image/png'},
                         {'src':'images/item3192.png', 'size':'192x192',
                          'type':'image/png'}]
        # Item requirements
        item['requirements'] = {};
        item['requirements']['instant_payment'] = getItem(form.instant_payment.data, index)
        item['requirements']['subscription'] = getItem(form.subscription.data, index)
        item['modules'] = ['builder']
        # Image storage
        f = getItem(form.image.data, index)
        if f:
            filename = secure_filename(f.filename)
            src = os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename)
            f.save(src)
            item['primary_icon'] = {'src': '/static/' + filename, 'type': ''}
        else:
            item['primary_icon'] = {'src':False, 'type': False}
        print item
        items.append(item)
        draftJamla['items'] = items

    # Payment provider information
    draftJamla['payment_providers'] = {}
    draftJamla['payment_providers']['stripe'] = {}
    draftJamla['payment_providers']['gocardless'] = {}
    draftJamla['payment_providers']['paypal'] = {}

    # Paypal
    draftJamla['payment_providers']['paypal']['sepa_direct_supported'] = False
    draftJamla['payment_providers']['paypal']['subscription_supported'] = True
    draftJamla['payment_providers']['paypal']['instant_payment_supported'] = True
    draftJamla['payment_providers']['paypal']['variable_payments_supported'] = False

    # Stripe
    draftJamla['payment_providers']['stripe']['sepa_direct_supported'] = True
    draftJamla['payment_providers']['stripe']['subscription_supported'] = True
    draftJamla['payment_providers']['stripe']['instant_payment_supported'] = True
    draftJamla['payment_providers']['stripe']['variable_payments_supported'] = True
    draftJamla['payment_providers']['stripe']['publishable_key'] = ''
    draftJamla['payment_providers']['stripe']['secret_key'] = ''

    # Gocardless
    draftJamla['payment_providers']['gocardless']['sepa_direct_supported'] = True
    draftJamla['payment_providers']['gocardless']['subscription_supported'] = True
    draftJamla['payment_providers']['gocardless']['instant_payment_supported'] = True
    draftJamla['payment_providers']['gocardless']['variable_payments_supported'] = True
    draftJamla['payment_providers']['gocardless']['access_token'] = ''
    draftJamla['payment_providers']['gocardless']['environment'] = ''


    subdomain = create_subdomain_string(draftJamla)
    session['site-url'] = 'https://' + subdomain.lower() + '.subscriby.shop'
    stream = file(subdomain + '.yaml', 'w')
    # Save to yml
    yaml.safe_dump(draftJamla, stream,default_flow_style=False)
    # Generate site
    create_subdomain(jamla=draftJamla)
    url = 'https://' + request.host + '/activate/' + subdomain
    return redirect(url) 

@app.route('/activate/<sitename>')
def choose_package(sitename=None):
    try:
        plan = session['plan']
        if session['plan'] and is_valid_sku(plan):
           return redirect(url_for('hedgehog.new_customer', plan=plan))
    except Exception:
        pass
    return render_template('select-package.html', jamla=jamla)

def journey_complete_subscriber(sender, **kw):
    print "Journery Complete! Send an email or something.."
    try:
        email = kw['email']
        sender = "hello@subscriptionwebsitebuilder.co.uk"
        login_url = session['login-url']
        msg  = Message(subject="Subscription Website Activated",
                       body=login_url,
                       sender=sender,
                       recipients=[email])
        mail.send(msg)
    except Exception:
        print "Error sending journey_complete_subscriber email"
        pass

def is_valid_sku(sku):
    for item in jamla['items']:
        if item['sku'] == sku:
            return True
    return False

def create_subdomain(jamla=None):
    subdomain = create_subdomain_string(jamla)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = [
        ('sub-auth-id', app.config["BUILDER_SUB_AUTH_ID"]),
        ('auth-password', app.config["BUILDER_SUB_AUTH_PASSWORD"]),
        ('domain-name', 'subscriby.shop'),
        ('record-type', 'A'),
        ('host', subdomain),
        ('record', app.config['KARMA_WEB_HOST']),
        ('ttl', 60),
    ]
    r = requests.post('https://api.cloudns.net/dns/add-record.json', headers=headers, data=data)
    deployJamla(subdomain + '.yaml')

@app.route('/sendJamla')
def deployJamla(filename):
    url = app.config['JAMLA_DEPLOY_URL']
    #Prepare post data
    multiple_files = [
    ]
    #Add jamla file to post data
    multiple_files.append(('file', (filename, open(filename, 'rb'))))
    #Get primary icons
    jamlaApp = Jamla()
    icon_paths = jamlaApp.get_primary_icons(jamlaApp.load(filename))
    for icon_path in icon_paths:
        iconFileName = os.path.split(icon_path)[1]
        src = os.path.join(app.config['UPLOADED_IMAGES_DEST'], iconFileName)
        multiple_files.append(('icons', (iconFileName, open(src, 'rb'))))

    r = requests.post(url, files=multiple_files)
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
