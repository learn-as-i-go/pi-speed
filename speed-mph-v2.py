#!/usr/bin/python3

import os
import sys
import signal
from time import *
from decimal import *
import serial
import threading
import csv
import re
import pygame
from pygame.locals import *
from datetime import datetime, timedelta
from picamera import PiCamera
from flask import Flask, render_template, request

# Flask setup
app = Flask(__name__)

# Debugging toggle
app.debug = True

# Define paths for CSV and images
csv_file_path = os.path.join(os.path.dirname(__file__), 'data', 'speed_data.csv')
images_folder = os.path.join(os.path.dirname(__file__), 'images')
print(csv_file_path)
print(images_folder)

# Ensure the images folder exists
if not os.path.exists(images_folder):
    os.makedirs(images_folder)

def save_data_to_csv(timestamp, speed_str, image_path):
    # Ensure the relative path is from the images directory
    #relative_image_path = os.path.relpath(image_path, start=os.path.join(os.path.dirname(__file__), 'images'))
    
    # Print statements to verify paths
    print(f"Saving data to CSV:")
    print(f"image path: {image_path}")
    #print(f"Relative image path: {relative_image_path}")
    
    # Write the CSV header if the file is new or empty
    if not os.path.exists(csv_file_path) or os.stat(csv_file_path).st_size == 0:
        with open(csv_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Speed (mph)", "Image Path"])

    # Append the new data to the CSV file
    with open(csv_file_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, speed_str, image_path])
    print(f"Data saved: Timestamp={timestamp}, Speed={speed_str}, Image={image_path}")



def get_latest_data():
    latest_entry = {'timestamp': 'N/A', 'speed': 'N/A', 'image': 'N/A'}
    if os.path.isfile(csv_file_path):
        with open(csv_file_path, mode='r') as file:
            reader = list(csv.DictReader(file))
            if reader:
                latest_entry = reader[-1]
    print(f"Latest data fetched: {latest_entry}")
    return latest_entry

def get_historical_data():
    historical_data = []
    if os.path.isfile(csv_file_path):
        with open(csv_file_path, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if 'image' in row:
                    # Ensure the image path is correctly handled
                    row['image'] = os.path.join('images', os.path.basename(row['image']))
                else:
                    row['image'] = 'N/A'
                
                # Print statements to verify paths
                print(f"Reading data from CSV:")
                print(f"Image path from CSV: {row['image']}")
                
                historical_data.append(row)
    return historical_data




@app.route('/')
def index():
    latest_data = get_latest_data()
    historical_data = get_historical_data()
    #latest_image_path = os.path.join('images', os.path.basename(latest_data['image']))
    latest_image_path = latest_data['image']
    print(f"Rendering with latest image path: {latest_image_path}")
    return render_template('index.html', latest_timestamp=latest_data['timestamp'],
                           latest_speed=latest_data['speed'], latest_image=latest_image_path,
                           historical_data=historical_data)


def run_flask():
    app.run(host='0.0.0.0', port=80, use_reloader=False)

# Flask server shutdown handling
def shutdown_server(signal, frame):
    print("\nShutting down Flask server...")
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, shutdown_server)
signal.signal(signal.SIGTERM, shutdown_server)

# Main script setup
Ops241A_Speed_Output_Units = 'US'
Ops241A_Speed_Output_Units_lbl = 'mph'
Ops241A_Blanks_Pref_Zero = 'BZ'
Ops241A_Min_Reported_Speed = 'R>5\n'
Ops241A_Sampling_Frequency = 'SV'
Ops241A_Transmit_Power = 'PD'    # mid power
Ops241A_Threshold_Control = 'MX' # 1000 magnitude-square
Ops241A_Module_Information = '??'

logo_height = 73
logo_width = 400

use_LCD = True
if use_LCD:
    os.environ['SDL_VIDEODRIVER'] = 'fbcon'
    os.environ["SDL_FBDEV"] = "/dev/fb1"
    screen_size = (480, 320)
else:
    print("Not configured for TFT display")
    screen_size = (640, 480)

pygame.init()
pygame.display.init()
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
screen = pygame.display.set_mode(screen_size)
screen_size_width = screen_size[0]
screen_size_height = screen_size[1]
units_lbl_font_size = int(screen_size_width / 10)
pygame.display.set_caption("OmniPreSense Radar")

screen_bkgnd_color = (0x30, 0x39, 0x86)
screen.fill(screen_bkgnd_color)
logo = pygame.image.load('/home/pi/OPS241A_RasPiLCD/ops_logo_400x73.jpg')
logo_x = (screen_size_width - logo_width) / 2
screen.blit(logo, (logo_x, 1))

speed_font_size = 180
speed_font_name = "Consolas"
speed_font = pygame.font.SysFont(speed_font_name, speed_font_size, True, False)
speed_col = int(screen_size[0] / 4)
speed_row = logo_height + int(speed_font_size * 0.3)

units_lbl_font = pygame.font.SysFont(speed_font_name, units_lbl_font_size, True, False)
units_lbl = units_lbl_font.render("mph", True, WHITE)
units_lbl_col = int(3 * (screen_size[0] / 4))
units_lbl_row = (speed_row + speed_font_size) - (2 * units_lbl_font_size)
screen.blit(units_lbl, [units_lbl_col, units_lbl_row])

pygame.display.flip()

ser = serial.Serial(
    port='/dev/ttyACM0',
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1,
    writeTimeout=2
)
ser.flushInput()
ser.flushOutput()

camera = PiCamera()
camera.resolution = (1024, 768)
camera.rotation = 180

def capture_image(image_path):
    print(f"Capturing image with path: {image_path}")
    camera.capture(image_path)
    print(f"Photo captured: {image_path}")


def send_serial_cmd(print_prefix, command):
    data_for_send_str = command
    data_for_send_bytes = str.encode(data_for_send_str)
    print(print_prefix, command)
    ser.write(data_for_send_bytes)
    ser_write_verify = False
    ser_message_start = '{'
    while not ser_write_verify:
        data_rx_bytes = ser.readline()
        if len(data_rx_bytes) != 0:
            data_rx_str = str(data_rx_bytes)
            if data_rx_str.find(ser_message_start):
                ser_write_verify = True

print("\nInitializing Ops241A Module")
send_serial_cmd("\nSet Speed Output Units: ", Ops241A_Speed_Output_Units)
send_serial_cmd("\nSet Sampling Frequency: ", Ops241A_Sampling_Frequency)
send_serial_cmd("\nSet Transmit Power: ", Ops241A_Transmit_Power)
send_serial_cmd("\nSet Threshold Control: ", Ops241A_Threshold_Control)
send_serial_cmd("\nSet Blanks Preference: ", Ops241A_Blanks_Pref_Zero)
send_serial_cmd("\nSet Reported MinSpeed: ", Ops241A_Min_Reported_Speed)

# Start Flask server in a separate thread
flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Main loop
done = False
while not done:
    try:
        Ops241_rx_bytes = ser.readline()
        
        if len(Ops241_rx_bytes) == 0:
            print("No data received from OPS241A")
            continue
        
        Ops241_rx_str = str(Ops241_rx_bytes)
        print("RX:" + Ops241_rx_str)
        
        if Ops241_rx_str.find('{') == -1:
            try:
                Ops241_rx_float = float(Ops241_rx_bytes)
                speed_available = True
            except ValueError:
                print("Unable to convert to a number: " + Ops241_rx_str)
                speed_available = False

        if speed_available:
            pygame.draw.rect(screen, screen_bkgnd_color,
                             (speed_col, speed_row, screen_size_width - speed_col, speed_font_size), 0)
            speed_rnd = round(Ops241_rx_float, 1)
            speed_str = str(speed_rnd)
            if speed_rnd < 0:
                speed_rend = speed_font.render(speed_str, True, WHITE)
            elif speed_rnd > 0:
                speed_rend = speed_font.render(speed_str, True, RED)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                image_path = os.path.join('images', f"car_{timestamp}_{speed_str}.jpg")
                
                # Create and start the image capture thread
                image_thread = threading.Thread(target=capture_image, args=(image_path,))
                image_thread.start()
                
                # Wait for the image capture thread to complete
                image_thread.join()
                
                # Save data after image capture completes
                save_data_to_csv(timestamp, speed_str, image_path)
            else:
                speed_rend = speed_font.render(speed_str, True, WHITE)

            screen.blit(speed_rend, [speed_col, speed_row])
            screen.blit(units_lbl, [units_lbl_col, units_lbl_row])

            pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                camera.close()
                exit()

    except serial.SerialException as e:
        print(f"Serial exception: {e}")
        ser.flushInput()
        continue
