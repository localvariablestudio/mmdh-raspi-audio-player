import RPi.GPIO as GPIO
from time import sleep

# Global GPIO config
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Audio control
play_status = False

# Pins config
btn1 = [2, 3]
GPIO.setup(btn1[0], GPIO.IN, pull_up_down=GPIO.PUD_UP)

def event_catch(ch):
    # play_status = not play_status
    # print('Play status: ', play_status)
    print(ch)

GPIO.add_event_detect(btn1[0], GPIO.FALLING, callback=event_catch, bouncetime=100)

while True:
    pass