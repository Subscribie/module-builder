import os, re
from flask import Flask, render_template, session, redirect, url_for, escape, request, current_app as app
from werkzeug.utils import secure_filename
from jamla import Jamla
jamla = Jamla.load(app.config['JAMLA_PATH'])

from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, FieldList, FileField, validators, BooleanField, TextField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileAllowed, FileRequired
from flask_uploads import UploadSet, IMAGES
import yaml
from yaml import load, dump
import requests
from base64 import urlsafe_b64encode

# Load builder module env
curDir = os.path.dirname(os.path.realpath(__file__))
app.config.from_pyfile('/'.join([curDir, '.env']))

class ItemsForm(FlaskForm):
    title = FieldList(StringField('Title', [validators.DataRequired()]), min_entries=1)
    company_name = TextField('company_name')
    instant_payment = FieldList(BooleanField('Up-Front Payment'), min_entries=1)
    subscription = FieldList(BooleanField('Subscription'), min_entries=1)
    sell_price = FieldList(FloatField('Sell Price'), min_entries=1)
    monthly_price = FieldList(FloatField('Monthly Price'), min_entries=1)
    selling_points = FieldList(FieldList(StringField('Unique Selling Point', [validators.DataRequired()]), min_entries=3), min_entries=1)
    images = UploadSet('images', IMAGES)
    image = FieldList(FileField(validators=[FileAllowed(images, 'Images only!')]), min_entries=1)

@app.route('/start-building', methods=['GET'])
def start_building():
    form = ItemsForm()
    return render_template('start-building.html', jamla=jamla, form=form)



@app.route('/start-building', methods=['POST'])
def save_items():
    draftJamla = {}
    form = ItemsForm()
    draftJamla['version'] = 1
    company_name = form.company_name.data
    draftJamla['company'] = {'name':company_name, 'logo':'', 'start_image':''}
    items = []
    for index, item in enumerate(form.title.data):
        item = {}
        item['title'] = getItem(form.title.data, index)
        item['sku'] = getItem(form.title.data, index)
        item['sell_price'] = getItem(form.sell_price.data, index) or 0
        item['sell_price'] = item['sell_price'] * 100  
        item['monthly_price'] = getItem(form.monthly_price.data, index) or 0
        item['monthly_price'] = item['monthly_price'] * 100 
        item['subscription'] = getItem(form.subscription.data, index)
        item['instant_payment'] = getItem(form.instant_payment.data, index)
        item['selling_points'] = getItem(form.selling_points.data, index)
        item['subscription_terms'] = {'minimum_term_months': 12}
        item['primary_colour'] = "#e73b1a"
        item['icons'] = [{'src':'images/item3148.png', 
                          'size':'48x48', 'type':'image/png'},
                         {'src':'images/item3192.png', 'size':'192x192',
                          'type':'image/png'}]
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

    subdomain = create_subdomain_string(draftJamla)
    stream = file(subdomain + '.yaml', 'w')
    # Save to yml
    yaml.dump(draftJamla, stream,default_flow_style=False)
    # Generate site
    create_subdomain(jamla=draftJamla)
            
    return redirect('/preview?mysite=' + subdomain) 

@app.route('/preview', methods=['GET'])
def preview():
    """ Preview site before checking out."""
    name = str(request.args.get('mysite'))
    jamla = Jamla.load(name + '.yaml')
    return render_template('preview-store.html', jamla=jamla)

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
    icon_paths = Jamla.get_primary_icons(Jamla.load(filename))
    for icon_path in icon_paths:
        iconFileName = os.path.split(icon_path)[1]
        src = os.path.join(app.config['UPLOADED_IMAGES_DEST'], iconFileName)
        multiple_files.append(('icons', (iconFileName, open(src, 'rb'))))

    r = requests.post(url, files=multiple_files)
    return "Sent jamla file for deployment"

def create_subdomain_string(jamla=None):
    if jamla is None:
        subdomain = urlsafe_b64encode(os.urandom(5)).replace('=', '')
    else: 
        subdomain = re.sub(r'\s+', '', jamla['company']['name'])
    return subdomain


def getItem(container, i, default=None):
    try:
        return container[i]
    except IndexError:
        return default
