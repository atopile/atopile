from flask import Flask, send_from_directory
import os

app = Flask(__name__, static_folder='dist', static_url_path='')

current_dir = os.path.dirname(os.path.abspath(__file__))
data_file_path = os.path.join(current_dir, 'index.html')

@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True, port=8080)