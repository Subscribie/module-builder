import os, errno, shutil, subprocess
from flask import Flask, request, redirect, url_for
from werkzeug.utils import secure_filename
import git

app = Flask(__name__)
app.config.from_envvar('DEPLOYER_SETTINGS')

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
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
	# Clone hedgehog repo
        try:
            git.Git(dstDir).clone("git@gitlab.com:karmacrew/hedgehog.git")
        except:
            pass
        file.save(os.path.join(dstDir, filename + '.yaml'))
        # Generate .env file
        shutil.copy2(dstDir + 'hedgehog/shortly/.env.example', dstDir + 'hedgehog/shortly/.env')
        # Copy Jamla file into repo
        shutil.move(dstDir + filename + '.yaml', dstDir + 'jamla.yaml')
        import pdb;pdb.set_trace()
        # Set JAMLA path
        jamlaPath = dstDir + 'jamla.yaml'
        fp = open(dstDir + "hedgehog/shortly/.env", "a+")
        fp.write('JAMLA_PATH="' + jamlaPath + '"' + "\n")
        fp.close()

        # Append new site to apache config
        vhost = "Use VHost " + webaddress + " " app.config['APACHE_USER'] + " " + dstDir
	fp = open(app.config['APACHE_CONF_FILE'], "a+")
        fp.write(vhost + "\n")
        fp.close()
        # Reload apache with new vhost
        subprocess.call("sudo /etc/init.d/apache2 reload", shell=True)

        
        return 'Stored & crated site'

    return "Deployed site probably!"

application = app
