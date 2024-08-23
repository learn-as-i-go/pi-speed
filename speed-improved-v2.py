#!/usr/bin/python3

# Import time, decimal, serial, GPIO, reg expr, sys, and pygame modules
import os
import sys
from time import *
from decimal import *
import serial
import re
import pygame
from pygame.locals import *
from datetime import datetime, timedelta
import picamera
from PIL import Image, ImageDraw, ImageFont
import csv
import subprocess
import threading

# Initialize global variable for Flask server process
flask_process = None

def start_flask_server():
    global flask_process
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, 'app.py')
    flask_process = subprocess.Popen(['python3', app_path])

def terminate_flask_server():
    global flask_process
    if flask_process:
        flask_process.terminate()
        flask_process.wait()

def signal_handler(sig, frame):
    print('Terminating Flask server...')
    terminate_flask_server()
    pygame.quit()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Ops241A module settings
Ops241A_Speed_Output_Units = ['US','UK','UM','UC']
Ops241A_Speed_Output_Units_lbl = ['mph','km/h','m/s','cm/s']
OPS_current_units = 3
Ops241A_Blanks_Pref_Zero = 'BZ'
Ops241A_Sampling_Frequency = 'SV'
Ops241A_Transmit_Power = 'PD'    # miD power
Ops241A_Threshold_Control = 'MX' # 1000 magnitude-square. 10 as reported
Ops241A_Module_Information = '??'

logo_height = 73
logo_width = 400

use_LCD = True
if use_LCD:
    # Display screen width and height
    os.environ['SDL_VIDEODRIVER'] = 'fbcon'
    os.environ["SDL_FBDEV"] = "/dev/fb1"
    screen_size = (480, 320)
else:
    print("Not configured for TFT display")
    screen_size = (640, 480)

# Initialize pygame graphics and sound
print("Initializing pygame graphics")
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

# Initialize the display
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
units_lbl = units_lbl_font.render("m/s", True, WHITE)
units_lbl_col = int(3 * (screen_size[0] / 4))
units_lbl_row = (speed_row + speed_font_size) - (2 * units_lbl_font_size)
screen.blit(units_lbl, [units_lbl_col, units_lbl_row])

# Update screen
pygame.display.flip()

# Initialize the USB port to read from the OPS-241A module
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

# Initialize the camera
camera = picamera.PiCamera()

# CSV file path
csv_file_path = '/home/pi/OPS241A_RasPiLCD/motion_data.csv'

def send_serial_cmd(print_prefix, command):
    data_for_send_str = command
    data_for_send_bytes = str.encode(data_for_send_str)
    print(print_prefix, command)
    ser.write(data_for_send_bytes)
    ser_message_start = '{'
    ser_write_verify = False
    while not ser_write_verify:
        data_rx_bytes = ser.readline()
        data_rx_length = len(data_rx_bytes)
        if (data_rx_length != 0):
            data_rx_str = str(data_rx_bytes)
            if data_rx_str.find(ser_message_start) != -1:
                ser_write_verify = True

def initialize_csv_file():
    with open(csv_file_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'Speed (m/s)'])

def log_data_to_csv(timestamp, speed):
    with open(csv_file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([timestamp, speed])

def capture_image_with_timestamp():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'/home/pi/OPS241A_RasPiLCD/images/image_{timestamp}.jpg'
    
    camera.capture(filename)
    
    image = Image.open(filename)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    text_position = (10, 10)
    draw.text(text_position, text, font=font, fill='white')
    image.save(filename)
    
    print(f'Image captured and saved as {filename}')

# Start the Flask server in a separate thread
threading.Thread(target=start_flask_server, daemon=True).start()

# Main Loop
initialize_csv_file()
last_units_change = datetime.now()
interval_timedelta = timedelta(seconds=10)
done = False
while not done:
    speed_available = False
    Ops241_rx_bytes = ser.readline()
    Ops241_rx_bytes_length = len(Ops241_rx_bytes)
    if (Ops241_rx_bytes_length != 0):
        Ops241_rx_str = str(Ops241_rx_bytes)
        print("RX:" + Ops241_rx_str)
        if Ops241_rx_str.find('{') == -1:
            try:
                Ops241_rx_float = float(Ops241_rx_bytes)
                speed_available = True
            except ValueError:
                print("Unable to convert to a number the string:" + Ops241_rx_str)
                speed_available = False

    if speed_available:
        pygame.draw.rect(
            screen,
            screen_bkgnd_color,
            (speed_col, speed_row, screen_size_width - speed_col, speed_font_size),
            0)
        speed_rnd = round(Ops241_rx_float, 1)
        speed_str = str(speed_rnd)
        if speed_rnd < 0:
            speed_rend = speed_font.render(speed_str, True, WHITE)
        elif speed_rnd > 0:
            speed_rend = speed_font.render(speed_str, True, RED)
        else:
            speed_rend = speed_font.render(speed_str, True, WHITE)
        screen.blit(speed_rend, [speed_col, speed_row])
        screen.blit(units_lbl, [units_lbl_col, units_lbl_row])

        # Capture image with timestamp if speed is detected
        capture_image_with_timestamp()
        
        # Log data to CSV
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_data_to_csv(timestamp, speed_rnd)

        # Update screen
        pygame.display.flip()

    now = datetime.now()
    if (last_units_change + interval_timedelta) < now:
        if OPS_current_units == len(Ops241A_Speed_Output_Units) - 1:
            OPS_current_units = 0
        else:
            OPS_current_units += 1
        send_serial_cmd("\nSet Speed Output Units: ", Ops241A_Speed_Output_Units[OPS_current_units])
        units_lbl = units_lbl_font.render(Ops241A_Speed_Output_Units_lbl[OPS_current_units], True, WHITE)
        last_units_change = now

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            terminate_flask_server()
            sys.exit(0)