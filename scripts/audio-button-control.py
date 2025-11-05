import RPi.GPIO as GPIO
from time import sleep

pin_in = 2

GPIO.setmode(GPIO.BCM)

GPIO.setup(pin_in, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def event_catch():
    print('Button down')

GPIO.add_event_detect(pin_in, GPIO.FALLING, callback=event_catch)