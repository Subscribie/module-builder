import os
from flask import Flask, render_template, session, redirect, url_for, escape, request, current_app as app
from werkzeug.utils import secure_filename
from jamla import Jamla
jamla = Jamla.load(app.config['JAMLA_PATH'])

from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, FieldList, FileField, validators, BooleanField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileAllowed, FileRequired
from flask_uploads import UploadSet, IMAGES
import yaml
from yaml import load, dump


class ItemsForm(FlaskForm):
    title = FieldList(StringField('Title', [validators.DataRequired()]), min_entries=1)
    instant_payment = FieldList(BooleanField('Up-Front Payment'), min_entries=1)
    subscription = FieldList(BooleanField('Subscription'), min_entries=1)
    sell_price = FieldList(FloatField('Price'), min_entries=1)
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
    draftJamla['version'] = 1
    draftJamla['company'] = {'name':'Karma', 'logo':'', 'start_image':''}
    items = []
    form = ItemsForm()
    for index, item in enumerate(form.title.data):
        item = {}
        item['title'] = getItem(form.title.data, index)
        item['sku'] = getItem(form.title.data, index)
        item['sell_price'] = getItem(form.sell_price.data, index) or 0
        item['monthly_price'] = getItem(form.monthly_price.data, index) or 0
        item['subscription'] = getItem(form.subscription.data, index)
        item['instant_payment'] = getItem(form.instant_payment.data, index)
        item['selling_points'] = getItem(form.selling_points.data, index)
        item['subscription_terms'] = {'minimum_term_months': 12}
        item['primary_colour'] = "#e73b1a"
        item['primary_icon'] = {'src':'/static/item3.svg', 'type': 'image/svg+xml'}
        item['icons'] = [{'src':'images/item3148.png', 
                          'size':'48x48', 'type':'image/png'},
                         {'src':'images/item3192.png', 'size':'192x192',
                          'type':'image/png'}]
        item['modules'] = ['builder']
        # Image storage
        f = getItem(form.image.data, index)
        if f:
            filename = secure_filename(f.filename)
            f.save(os.path.join(
                app.config['UPLOADED_IMAGES_DEST'], filename
            ))
        print item
        items.append(item)
        draftJamla['items'] = items
        stream = file('document.yaml', 'w')
        # Save to yml
        yaml.dump(draftJamla, stream,default_flow_style=False)
            
    return redirect('/preview') 

@app.route('/preview', methods=['GET'])
def preview():
    """ Preview site before checking out."""
    jamla = Jamla.load(os.path.join(app.instance_path, 'document.yaml'))
    return render_template('preview-store.html', jamla=jamla)

def getItem(container, i, default=None):
    try:
        return container[i]
    except IndexError:
        return default

