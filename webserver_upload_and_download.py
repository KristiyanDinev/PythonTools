# python -m pip install flask
from flask import Flask, flash, request, redirect, url_for
from flask import send_from_directory, send_file

from werkzeug.utils import secure_filename

import os

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = ".\\files"

app.config['ALLOWED_EXTENSIONS'] = {'.mp3', '.wav'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)



@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == "POST":
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
            
        file = request.files['file']

        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('download_file', name=filename))
        
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''


if __name__ == '__main__':
    app.run(port=5000,debug=True) 

