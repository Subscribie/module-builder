import os
from flask import Flask, request, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)

@app.route('/deploy', methods=['GET', 'POST'])
def deploy():
    import pdb;pdb.set_trace()
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    # if user does not select file, browser also
    # submit a empty part without filename
    if file.filename == '':
        return 'No selected file'
       
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join('./', filename))
        return 'Stored'

    return "Deployed site probably!"
