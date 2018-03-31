from flask import Flask, render_template, session, redirect, url_for, escape, request, current_app as app
from werkzeug.utils import secure_filename
from jamla import Jamla
jamla = Jamla.load(app.config['JAMLA_PATH'])

from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, FieldList, FileField, validators, BooleanField
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileRequired


class MyForm(FlaskForm):
    name = StringField('Name', [validators.DataRequired()])
    instant_payment = FieldList(BooleanField('Up-Front Payment'), min_entries=1)
    subscription = FieldList(BooleanField('Subscription'), min_entries=1)
    sell_price = FieldList(DecimalField('Price'), min_entries=1)
    monthly_price = FieldList(DecimalField('Monthly Price'), min_entries=1)
    selling_points = FieldList(StringField('Unique Selling Point', [validators.DataRequired()]), min_entries=3)
    image = FieldList(FileField(), min_entries=1)

@app.route('/start-building', methods=['GET'])
def start_building():
    form = MyForm()
    return render_template('products.html', jamla=jamla, form=form)

@app.route('/start-building', methods=['POST'])
def save_items():
    print request.form
    return render_template('preview-store.html', jamla=jamla)
