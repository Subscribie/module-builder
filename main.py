import os, errno, shutil
from urllib.request import urlopen
import subprocess
from flask import Flask, request, redirect, url_for
from werkzeug.utils import secure_filename
import git
import yaml
import sqlite3
import datetime
from base64 import b64encode, urlsafe_b64encode
import random

app = Flask(__name__)
# Load .env settings
curDir = os.path.dirname(os.path.realpath(__file__))
app.config.from_pyfile('/'.join([curDir, '.env']))

@app.route('/', methods=['GET', 'POST'])
@app.route('/deploy', methods=['GET', 'POST'])
def deploy():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    # if user does not select file, browser also
    # submit a empty part without filename
    if file.filename == '':
        return 'No selected file'
    if file:
        # Store submitted jamla file in its site folder
        filename = secure_filename(file.filename)
        filename = filename.split('.')[0]
        webaddress = filename.lower() + '.subscriby.shop'
        # Create directory for site
        try:
            dstDir = app.config['SITES_DIRECTORY'] + webaddress + '/'
            os.mkdir(dstDir)
            file.save(os.path.join(dstDir, filename + '.yaml'))
            # Rename to jamla.yaml
            shutil.move(os.path.join(dstDir, filename + '.yaml'), dstDir + 'jamla.yaml')
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
	    # Clone subscribie repo & set-up .env files
        try:
            git.Git(dstDir).clone("https://github.com/Subscribie/subscribie")
            # Generate config.py file
            response = urlopen('https://raw.githubusercontent.com/Subscribie/subscribie/master/subscribie/config.py.example')
            configfile = response.read()
            with open(dstDir + 'subscribie' + '/instance/config.py', 'wb') as fh:
                fh.write(configfile)

        except Exception as e:
            print("Did not clone subscribie for some reason")
            print(e.message, e.args)
            pass
        # Clone Subscriber Matching Service
        try:
            git.Git(dstDir).clone('https://github.com/Subscribie/subscription-management-software')
        except Exception as e:
            print("Didn't clone subscriber matching service")
            print(e.message, e.args)

        # Run subscribie_cli init
        subprocess.call('subscribie init', cwd= ''.join([dstDir, 'subscribie']), shell=True)
        shutil.move(''.join([dstDir, 'subscribie/', 'data.db']), dstDir)
        # Run subscribie_cli migrations
        subprocess.call('subscribie migrate --DB_FULL_PATH ' + dstDir + \
                          'data.db', \
                          cwd = ''.join([dstDir, 'subscribie']), shell=True)

        # Seed users table with site owners email address so they can login
        fp = open(dstDir + 'jamla.yaml', 'r')
        jamla =  yaml.load(fp)
        for email in jamla['users']:
            con = sqlite3.connect(dstDir + 'data.db')
            con.text_factory = str
            cur = con.cursor()                                                   
            now = datetime.datetime.now()
            login_token = str(urlsafe_b64encode(os.urandom(24)))
            cur.execute("INSERT INTO user (email, created_at, active, login_token) VALUES (?,?,?,?)", (email, now, 1, login_token,)) 
            con.commit()                                                         
            con.close()
        
        # Set JAMLA path, STATIC_FOLDER, and TEMPLATE_FOLDER
        jamlaPath = dstDir + 'jamla.yaml'
        cliWorkingDir = ''.join([dstDir, 'subscribie'])
        theme_folder = ''.join([dstDir, 'subscribie', '/themes/'])
        static_folder = ''.join([theme_folder, 'theme-jesmond/static/'])

        settings = ' '.join([
            '--JAMLA_PATH', jamlaPath,
            '--TEMPLATE_FOLDER', theme_folder,
            '--STATIC_FOLDER', static_folder, 
            '--UPLOADED_IMAGES_DEST', dstDir + 'static/',
            '--DB_FULL_PATH', dstDir + 'data.db',
            '--SUCCESS_REDIRECT_URL', 'https://' + webaddress + '/complete_mandate',
            '--THANKYOU_URL', 'https://' + webaddress + '/thankyou',
            '--EMAIL_HOST', app.config['DEPLOY_EMAIL_HOST'],
            '--MAIL_SERVER', app.config['MAIL_SERVER'],
            '--MAIL_PORT', "25",
            '--MAIL_DEFAULT_SENDER', app.config['EMAIL_LOGIN_FROM'],
            '--MAIL_USERNAME', app.config['MAIL_USERNAME'],
            '--MAIL_PASSWORD', ''.join(['"', app.config['MAIL_PASSWORD'], '"']),
            '--MAIL_USE_TLS' , app.config['MAIL_USE_TLS'],
            '--EMAIL_LOGIN_FROM', app.config['EMAIL_LOGIN_FROM'],
            '--GOCARDLESS_CLIENT_ID', app.config['DEPLOY_GOCARDLESS_CLIENT_ID'],
            '--GOCARDLESS_CLIENT_SECRET', app.config['DEPLOY_GOCARDLESS_CLIENT_SECRET'],
        ])
        subprocess.call('subscribie setconfig ' + settings, cwd = cliWorkingDir\
                          , shell=True)

        fp.close()

        fp = open(dstDir + 'jamla.yaml', 'w+')
        jamla['modules_path'] = dstDir + 'subscription-management-software'
        output = yaml.dump(jamla)
        fp.write(output)
        fp.close()
        # Store submitted icons in sites staic folder
        if 'icons' in request.files:
            for icon in request.files.getlist('icons'):
                iconFilename = secure_filename(icon.filename)
                icon.save(os.path.join(static_folder, iconFilename))
        # Append new site to apache config
        vhost = " ".join(["Use VHost", webaddress, app.config['APACHE_USER'], dstDir])
        ssl = " ".join(["Use SSL", webaddress, '443', app.config['APACHE_USER'], dstDir])
        #Verify Vhost isn't already present
        try: 
            fp = open(app.config['APACHE_CONF_FILE'], "a+")
            for line in fp:
                if webaddress in line:
                    fp.close()
                    raise

            fp = open(app.config['APACHE_CONF_FILE'], "a+")
            fp.write(vhost + "\n")
            fp.write(ssl + "\n")
            fp.close()
        except:
            print ("Skipping as " + webaddress + "already exists.")
            pass

        try:
            # Reload apache with new vhost
            subprocess.call("sudo /etc/init.d/apache2 graceful", shell=True)
        except Exception as e:
            print ("Problem reloading apache:")
            print (e)
            pass
    login_url = ''.join(['https://', webaddress, '/login/', login_token])

    return login_url

application = app
