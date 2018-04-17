import os, errno, shutil, subprocess
from flask import Flask, request, redirect, url_for
from werkzeug.utils import secure_filename
import git

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
                print "Error creating or moving data.db in createdb.py")
                pass

            # Set JAMLA path, STATIC_FOLDER, and TEMPLATE_FOLDER
            jamlaPath = dstDir + 'jamla.yaml'
            fp = open(dstDir + "hedgehog/shortly/.env", "a+")
            fp.write(''.join(['JAMLA_PATH="', jamlaPath, '"', "\n"]))
            fp.write(''.join(['STATIC_FOLDER="../../static','"',"\n"]))
            fp.write(''.join(['TEMPLATE_FOLDER="../../templates','"',"\n"]))
            fp.write(''.join(['DB_FULL_PATH=', dstDir,"\n"]))
            fp.close()
            # Store submitted icons in sites staic folder
            if 'icons' in request.files:
                for icon in request.files.getlist('icons'):
                    iconFilename = secure_filename(icon.filename)
                    icon.save(os.path.join(dstDir + 'static', iconFilename))
            # Append new site to apache config
            vhost = " ".join(["Use VHost", webaddress, app.config['APACHE_USER'], dstDir])
            #Verify Vhost isn't already present
            try: 
                fp = open(app.config['APACHE_CONF_FILE'], "a+")
                for line in fp:
                    if webaddress in line:
                        fp.close()
                        raise

                fp = open(app.config['APACHE_CONF_FILE'], "a+")
                fp.write(vhost + "\n")
                fp.close()
                # Reload apache with new vhost
                subprocess.call("sudo /etc/init.d/apache2 reload", shell=True)
            except:
                print "Skipping as " + webaddress + "already exists."
                pass
        except:
            pass #Failed to deploy Hedgehog

        
        # Clone Crab repo for instant payments & set-up .env files
        try:
            git.Git(dstDir).clone("git@gitlab.com:karmacrew/Crab.git")

            # Generate .env file
            shutil.copy2(dstDir + 'Crab/.env.example', dstDir + 'Crab/.env')
            # Set .env values
            fp = open(dstDir + "Crab/.env", "a+")
            fp.write(''.join(['ENV="', 'testing', "\n"]))
            fp.write(''.join(['CRAB_IP="', '127.0.0.1', "\n"]))
            fp.write(''.join(['CRAB_PORT=', '5001', "\n"]))
            fp.write(''.join(['STRIPE_API_KEY=', 'sk_test_D1dVenFiwWCObU7vUFHbWgdN', "\n"]))
            fp.write(''.join(['DB_PATH=', '../../data.db', "\n"]))
            fp.write(''.join(['ON_SUCCESS_URL=','https://', webaddress, '/establish_mandate', "\n"]))
            fp.write(''.join(['JAMLA_PATH=','../jamla.yaml', "\n"]))
            fp.close()
        except:
            print "Problem cloning Crab"
            pass
        
        return 'Stored & crated site'

    return "Deployed site probably!"

application = app
