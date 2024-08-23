from flask import Flask, send_from_directory, jsonify
import csv
import os

app = Flask(__name__)

# Define the path for static files
STATIC_FOLDER = 'templates'
app = Flask(__name__, static_folder=STATIC_FOLDER)

@app.route('/')
def index():
    return send_from_directory(STATIC_FOLDER, 'index.html')

@app.route('/data')
def get_data():
    data = []
    csv_file_path = '/home/pi/OPS241A_RasPiLCD/motion_data.csv'
    if os.path.exists(csv_file_path):
        with open(csv_file_path, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                data.append(row)
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
