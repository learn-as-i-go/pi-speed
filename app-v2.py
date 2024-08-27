from flask import Flask, render_template
import csv
import os

app = Flask(__name__)

# Define paths
csv_file_path = '/home/pi/OPS241A_RasPiLCD/data.csv'
images_folder = '/home/pi/OPS241A_RasPiLCD/images/'

def get_latest_data():
    latest_entry = {'timestamp': 'N/A', 'speed': 'N/A', 'image': ''}
    with open(csv_file_path, mode='r') as file:
        reader = list(csv.DictReader(file))
        if reader:
            latest_entry = reader[-1]
    return latest_entry

def get_historical_data():
    historical_data = []
    with open(csv_file_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            historical_data.append(row)
    return historical_data

@app.route('/')
def index():
    latest_data = get_latest_data()
    historical_data = get_historical_data()
    return render_template('index.html', latest_timestamp=latest_data['timestamp'],
                           latest_speed=latest_data['speed'], latest_image=latest_data['image'],
                           historical_data=historical_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
