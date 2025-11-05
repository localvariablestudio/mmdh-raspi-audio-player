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
GPIO.setup(btn1[1], GPIO.OUT, initial=GPIO.LOW)

def event_catch(ch):
    global play_status
    play_status = not play_status
    print('Play status: ', play_status)
    GPIO.output(btn1[1], play_status)

GPIO.add_event_detect(btn1[0], GPIO.FALLING, callback=event_catch, bouncetime=100)

while True:
    pass