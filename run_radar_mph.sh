#!/bin/bash

echo "script started at $(date)" >> /home/pi/OPS241A_RasPiLCD/cron-log.txt

#set environment variables (adjust as needed)
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/sbin:/home/pi/.local/bin
export PYTHONPATH=/usr/lib/python3/dist-packages

echo "Environment variables set" >> /home/pi/OPS241A_RasPiLCD/cron-log.txt

#navigate to project directory
cd /home/pi/OPS241A_RasPiLCD

echo "Directory changed to $(pwd)" >> /home/pi/OPS241A_RasPiLCD/cron-log.txt

#verify Python version
python3 --version >> /home/pi/OPS241A_RasPiLCD/cron-log.txt 2>&1

#run script
sudo /usr/bin/python3 /home/pi/OPS241A_RasPiLCD/speed-mph-v2.py >> /home/pi/OPS241A_RasPiLCD/speed-mph-v2.log 2>&1

echo "python script executed" >> /home/pi/OPS241A_RasPiLCD/cron-log.txt
