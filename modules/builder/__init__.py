from flask import Flask, render_template, session, redirect, url_for, escape, request, current_app as app
from jamla import Jamla
jamla = Jamla.load(app.config['JAMLA_PATH'])

@app.route('/start-building', methods=['GET'])
def start_building():
        return render_template('products.html', jamla=jamla)
