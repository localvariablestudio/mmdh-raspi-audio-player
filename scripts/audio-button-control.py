import RPi.GPIO as GPIO
from time import sleep

# Global GPIO config
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pins config
pin_in = 2
GPIO.setup(pin_in, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def event_catch():
    print('Button down')

GPIO.add_event_detect(pin_in, GPIO.FALLING, callback=event_catch)