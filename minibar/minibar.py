#!/usr/bin/python3

import sys
import time
import pigpio
import RPi.GPIO as RPiGPIO
import copy
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from threading import Thread


# PWM values for lock-servo
LOCK_PWM_OPEN = 4
LOCK_PWM_CLOSED = .1

RPiGPIO.setwarnings(False)
RPiGPIO.setmode(RPiGPIO.BCM)

# PWM output for doorlock-servo
RPiGPIO.setup(2, RPiGPIO.OUT)
lock = RPiGPIO.PWM(2, 50) # 50 Hz
lock.start(0)

# Interrupt callbacks
cb = []

# trigger tick for each sensor tray
last_trigger = [0] * 5

# number of triggers for each sensor since last reset
sensor = [[0] * 8, [0] * 8, [0] * 8, [0] * 6, [0] * 4]

# filtered state for each sensor
tray = [[0] * 8, [0] * 8, [0] * 8, [0] * 6, [0] * 4]



# blocks for .3s
def moveLock(state): # 1 = open, 0 = closed
	lock.ChangeDutyCycle(LOCK_PWM_OPEN if state else LOCK_PWM_CLOSED)
	time.sleep(.3)
	lock.ChangeDutyCycle(0) # turn off servo


def filterSensors():
	for i in range(0,len(sensor)):
		filterTray(sensor[i], tray[i])

# Counted triggers are compared to a threshold to filter noise
def filterTray(sensor, tray):
	
	# The different types of trays run at different frequencies
	# 8 items -> 41 Hz
	# 6 items -> 55 Hz
	# 4 items -> 80 Hz
	threshold = 20
	if len(sensor) == 4:
		threshold = 40
	if len(sensor) == 6:
		threshold = 26
	
	for i in range(0,len(sensor)):
		tray[i] = 1 if sensor[i] > threshold else 0
		sensor[i] = 0


def trigger(GPIO, level, tick):
	global last_trigger
	global sensor

	# Ensure clean startup
	if last_trigger[0] == 0 and GPIO == 20: # Tray 1
		last_trigger[0] = tick
	if last_trigger[1] == 0 and GPIO == 13: # Tray 2
		last_trigger[1] = tick
	if last_trigger[2] == 0 and GPIO == 6: # Tray 4
		last_trigger[2] = tick
	if last_trigger[3] == 0 and GPIO == 7: # Tray 3
		last_trigger[3] = tick
	if last_trigger[4] == 0 and GPIO == 10: # Tray 5
			last_trigger[4] = tick


	# Different types of trays use slightly different timings
	if GPIO == 20:
		last_trigger[0] = tick
	if GPIO == 21:
		num = int(round(pigpio.tickDiff(last_trigger[0], tick) / 3200))
		if num >= 0 and num <= 7:
			sensor[0][num] += 1

	if GPIO == 13:
		last_trigger[1] = tick
	if GPIO == 16:
		num = int(round(pigpio.tickDiff(last_trigger[1], tick) / 3200))
		if num >= 0 and num <= 7:
			sensor[1][num] += 1

	if GPIO == 6:
		last_trigger[2] = tick
	if GPIO == 5:
		num = int(round(pigpio.tickDiff(last_trigger[2], tick) / 3200))
		if num >= 0 and num <= 7:
			sensor[2][num] += 1

	if GPIO == 7:
		last_trigger[3] = tick
	if GPIO == 8:
		num = int(round(pigpio.tickDiff(last_trigger[3], tick) / 3000))
		if num >= 0 and num <= 5:
			sensor[3][num] += 1

	if GPIO == 10:
		last_trigger[4] = tick
	if GPIO == 9:
		num = int(round(pigpio.tickDiff(last_trigger[4], tick) / 3000))
		if num >= 0 and num <= 3:
			sensor[4][num] += 1



# Activate triggers for all sensor inputs
pi = pigpio.pi()
cb.append(pi.callback(6, pigpio.RISING_EDGE, trigger))
cb.append(pi.callback(5, pigpio.RISING_EDGE, trigger))
cb.append(pi.callback(7, pigpio.RISING_EDGE, trigger))
cb.append(pi.callback(8, pigpio.RISING_EDGE, trigger))
cb.append(pi.callback(9, pigpio.RISING_EDGE, trigger))
cb.append(pi.callback(10, pigpio.RISING_EDGE, trigger))
cb.append(pi.callback(21, pigpio.RISING_EDGE, trigger))
cb.append(pi.callback(20, pigpio.RISING_EDGE, trigger))
cb.append(pi.callback(16, pigpio.RISING_EDGE, trigger))
cb.append(pi.callback(13, pigpio.RISING_EDGE, trigger))


# GET requestst to /open or /close move the lock
# All GET requests are answered with json containing sensor info
class Server(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(bytes(json.dumps({'bot': tray[0], 'mid': tray[2], 'top': tray[1], 'door_bot': tray[4], 'door_top': tray[3]}), "utf-8"))
        if "open" in self.path:
        	moveLock(1)
        elif "close" in self.path:
        	moveLock(0)
		
		
    def do_HEAD(self):
        self._set_headers()
        
    def log_message(self, format, *args):
        return


# Start webserver
server_address = ('', 8081)
httpd = HTTPServer(server_address, Server)
#httpd.serve_forever()
Thread(target=httpd.serve_forever).start()



# Main loop
try:
	while True:
		time.sleep(1)
		filterSensors()
except KeyboardInterrupt:
	for c in cb:
		c.cancel()
pi.stop()
