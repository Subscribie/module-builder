import os, shutil, subprocess
from flask import Flask, request, redirect, url_for
from werkzeug.utils import secure_filename
import git

app = Flask(__name__)

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
        filename = secure_filename(file.filename)
        file.save(os.path.join('/home/subwebbuild/www/sites/', filename))

        # Create directory for site
        filename = filename.split('.')[0]
	webaddress = filename.lower() + '.subscriby.shop'
        dstDir = '/home/subwebbuild/www/sites/' + webaddress
        os.mkdir(dstDir)
	# Clone hedgehog repo
        git.Git(dstDir).clone("git@gitlab.com:karmacrew/hedgehog.git")
	# Generate .env file
        shutil.copy2(dstDir + '/hedgehog/shortly/.env.example', dstDir + '/hedgehog/shortly/.env')
        # Copy Jamla file into repo
        shutil.move('/home/subwebbuild/' + filename + '.yaml', dstDir + '/jamla.yaml')
        # Set JAMLA path
        jamlaPath = dstDir + '/jamla.yaml'
	fp = open(dstDir + "/hedgehog/shortly/.env", "a+")
        fp.write('JAMLA_PATH="' + jamlaPath + '"' + "\n")
        fp.close()

        # Append new site to apache config
        vhost = "Use VHost " + webaddress + " subwebbuild /home/subwebbuild/www/sites/" + webaddress
	fp = open("/home/subwebbuild/www/sites/mass-virtual-hosting-jamla.conf", "a+")
        fp.write(vhost + "\n")
        fp.close()
        # Reload apache with new vhost
        subprocess.call("sudo /etc/init.d/apache2 reload", shell=True)

        
        return 'Stored & crated site'

    return "Deployed site probably!"

application = app
