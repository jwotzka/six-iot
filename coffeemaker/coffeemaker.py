#!/usr/bin/python3

import time
import RPi.GPIO as GPIO
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
import Adafruit_ADS1x15
import json

adc = Adafruit_ADS1x15.ADS1115()

# Temp in °C
coffee_temp = -1

# RPi pin numbers
BTN_ONE = 11 # out
BTN_TWO = 12 # out
LED_ONE = 22 # in
LED_TWO = 18 # in

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(LED_ONE, GPIO.IN)
GPIO.setup(LED_TWO, GPIO.IN)
GPIO.setup(BTN_ONE, GPIO.OUT)
GPIO.setup(BTN_TWO, GPIO.OUT)

# Ensure relais are open (active low)
GPIO.output(BTN_ONE, GPIO.HIGH)
GPIO.output(BTN_TWO, GPIO.HIGH)


# Blocks for 100ms
def pressBtn(gpio):
        GPIO.output(gpio, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(gpio, GPIO.HIGH)


one_laston = time.time()
one_lastoff = time.time()
two_laston = time.time()
two_lastoff = time.time()
def checkLEDs():
        global one_laston, one_lastoff, two_laston, two_lastoff
        if not GPIO.input(LED_ONE):
                one_laston = time.time()
        else:
                if time.time() - one_laston > 0.1:
                        one_lastoff = time.time()

        #if time.time() - one_laston > 1.5:
        #        print("OFF")
        #if time.time() - one_laston < 1.5 and time.time() - one_lastoff < 1.5:
        #        print("BLINK")
        #if time.time() - one_laston < 0.1 and time.time() - one_lastoff > 1.5:
        #        print("ON")


# Convert ADC input (mV) to °C
def calcTemp(adc):
    temp = 25 + (1500 - adc) / 30 # measured temp
    return (temp - 25) * 2 + 25 # compensate for sensor position

class Server(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        #self.wfile.write(bytes(json.dumps({'bot': tray_bot, 'mid': tray_mid, 'top': tray_top, 'door_bot': tray_door_bot, 'door_top': tray_door_top}), "utf-8"))
        if "one" in self.path:
        	pressBtn(BTN_ONE)
        elif "two" in self.path:
        	pressBtn(BTN_TWO)
        self.wfile.write(bytes(json.dumps({'temp': coffee_temp}),"utf-8"))
		
		
    def do_HEAD(self):
        self._set_headers()
        
    def log_message(self, format, *args):
        return
        
        
server_address = ('', 8081)
httpd = HTTPServer(server_address, Server)
Thread(target=httpd.serve_forever).start()


while 1:
        checkLEDs()
        time.sleep(.01)
        
        coffee_temp = calcTemp(adc.read_adc(0, gain=1) / 8)
    
