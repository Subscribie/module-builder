import os, errno, shutil
import subprocess32
from flask import Flask, request, redirect, url_for
from werkzeug.utils import secure_filename
import git
import yaml
import sqlite3
import datetime

app = Flask(__name__)
# Load .env settings
curDir = os.path.dirname(os.path.realpath(__file__))
app.config.from_pyfile('/'.join([curDir, '.env']))

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
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
	# Clone hedgehog repo & set-up .env files
        try:
            git.Git(dstDir).clone("git@gitlab.com:karmacrew/hedgehog.git")
            # Generate .env file
            shutil.copy2(dstDir + 'hedgehog/shortly/.env.example', dstDir + 'hedgehog/shortly/.env')
            # Copy Jamla file into repo
            shutil.move(dstDir + filename + '.yaml', dstDir + 'jamla.yaml')
            # Copy over default templates folder 
            shutil.copytree(dstDir + 'hedgehog/shortly/templates', dstDir + 'templates')
            # Copy over default static folder
            shutil.copytree(dstDir + 'hedgehog/shortly/static', dstDir + 'static')

            # Createsqlite3 db
            try:
                execfile(dstDir + '/hedgehog/shortly/createdb.py')
                shutil.move('data.db', dstDir)
            except:
                print "Error creating or moving data.db in createdb.py"
                pass
        except:
            pass #Did not clone Hedgehog

        # Run core migrations
        migrationsDir =  ''.join([dstDir, 'hedgehog/shortly/migrations/'])
        migrations = sorted(os.listdir(migrationsDir));

        for migration in migrations:
            subprocess32.call(''.join([migrationsDir, migration, ' -db ', dstDir, 'data.db -up']), shell=True)

        # Seed users table with site owners email address so they can login
        fp = open(dstDir + 'jamla.yaml', 'r')
        jamla =  yaml.load(fp)
        for email in jamla['users']:
            con = sqlite3.connect(dstDir + 'data.db')
            con.text_factory = str
            cur = con.cursor()                                                   
            now = datetime.datetime.now()
            random = str(os.urandom(24))
            cur.execute("INSERT INTO user (email, created_at, active, login_token) VALUES (?,?,?,?)", (email, now, 1, random,)) 
            con.commit()                                                         
            con.close()
        
        # Set JAMLA path, STATIC_FOLDER, and TEMPLATE_FOLDER
        jamlaPath = dstDir + 'jamla.yaml'
        fp = open(dstDir + "hedgehog/shortly/.env", "a+")
        fp.write(''.join(['JAMLA_PATH="', jamlaPath, '"', "\n"]))
        fp.write(''.join(['STATIC_FOLDER="../../static','"',"\n"]))
        fp.write(''.join(['TEMPLATE_FOLDER="../../templates','"',"\n"]))
        fp.write(''.join(['DB_FULL_PATH="', dstDir, 'data.db', '"', "\n"]))
        fp.write(''.join(['CRAB_URL="', 'https://', webaddress ,'/up-front-payment/', '"', "\n"]))
        fp.write(''.join(['GOCARDLESS_TOKEN="','sandbox_Di_44XAq2FlkshCOyIi7FmFUWQLSUHTEBxaCmE_p', '"',"\n"]))
        fp.write(''.join(['SUCCESS_REDIRECT_URL="','https://', webaddress, '/complete_mandate', '"',"\n"]))
        fp.write(''.join(['THANKYOU_URL="','https://', webaddress, '/thankyou', '"',"\n"]))
        fp.write(''.join(['EMAIL_HOST="', app.config['DEPLOY_EMAIL_HOST'], '"',"\n"]))

        fp.close()
        # Store submitted icons in sites staic folder
        if 'icons' in request.files:
            for icon in request.files.getlist('icons'):
                iconFilename = secure_filename(icon.filename)
                icon.save(os.path.join(dstDir + 'static', iconFilename))
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
            # Reload apache with new vhost
            subprocess32.call("sudo /etc/init.d/apache2 reload", shell=True)
        except:
            print "Skipping as " + webaddress + "already exists."
            pass

        
        # Clone Crab repo for instant payments & set-up .env files
        try:
            git.Git(dstDir).clone("git@gitlab.com:karmacrew/Crab.git")

            # Create .env file
            fp = open(dstDir + "Crab/.env", "a+")
            fp.write(''.join(['ENV="', 'testing', '"', "\n"]))
            fp.write(''.join(['CRAB_IP="', '127.0.0.1', '"', "\n"]))
            fp.write(''.join(['CRAB_PORT="', '5001', '"', "\n"]))
            fp.write(''.join(['STRIPE_API_KEY="',
                              'sk_test_D1dVenFiwWCObU7vUFHbWgdN', '"', "\n"]))
            fp.write(''.join(['ON_SUCCESS_URL="','https://', webaddress,
                              '/establish_mandate', '"', "\n"]))
            fp.write(''.join(['JAMLA_PATH="','../jamla.yaml', '"', "\n"]))
            fp.write(''.join(['DB_PATH="', dstDir , 'data.db', '"', "\n"]))
            fp.close()
            # Set stripe public env key
            shutil.move(dstDir + "Crab/js_env/STRIPE_PUBLIC_KEY.env.example",
                        dstDir + "Crab/js_env/STRIPE_PUBLIC_KEY.env")
            # Perform composer install
            subprocess32.Popen("composer install -d=" + dstDir + "Crab", shell=True, stdin=None, stdout=None, stderr=None, close_fds=True)
            return "Built site" # Allows Parent process to close cleanly

        except:
            print "Problem cloning Crab"
            pass
        
        return 'Stored & crated site'

    return "Deployed site probably!"

application = app
