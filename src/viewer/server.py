from flask import Flask, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
# Enable CORS for all domains on all routes
CORS(app)

current_dir = os.path.dirname(os.path.abspath(__file__))
data_file_path = os.path.join(current_dir, 'sample_data/default.view.json')

@app.route('/data')
def send_json():
    # Open the data.json file and load its contents
    with open(data_file_path, 'r') as file:
        data = json.load(file)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)