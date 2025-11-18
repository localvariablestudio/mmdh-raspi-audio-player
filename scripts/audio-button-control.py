import RPi.GPIO as GPIO
import alsaaudio
import wave
import threading

# Global GPIO config
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Audio control
play_status = [
    False,
    False,
    False,
    False,
    False,
    False
]

playback_thread = None  # Track the playback thread

prevCh = 0
# Pins config
buttons = [
    [2, 3],
    [4, 5],
    [6, 7]
    [8, 9],
    [10, 11],
    [16, 23]
]

buttonsDict = {
    2 : 0,
    4 : 1,
    6 : 2,
    8 : 3,
    10 : 4,
    16 : 23,
}

for i in range(len(buttons)):
    GPIO.setup(buttons[i][0], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(buttons[i][1], GPIO.OUT, initial=GPIO.LOW)    

def play_audio():
    """Play audio in a separate thread, checking play_status periodically"""
    global play_status
    try:
        # Open the WAV file
        f = wave.open('/home/control-1/Documents/mmdh-raspi-audio-player//assets/audio-test-2.wav', 'rb') 

        # Initialize a PCM device for playback
        # 'default' refers to the default sound card and device
        # You can specify a different device using 'hw:CARD=0,DEV=0' format
        out = alsaaudio.PCM(channels=f.getnchannels(), rate=f.getframerate(), format=alsaaudio.PCM_FORMAT_S16_LE, periodsize=1024, device='default')

        # Play the audio data
        data = f.readframes(1024)
        while data and play_status:  # Check play_status in the loop
            out.write(data)
            data = f.readframes(1024)
        
        # Clean up if playback was stopped
        if not play_status:
            print("Playback stopped by user")
        
        f.close()
        out.close()

    except alsaaudio.ALSAAudioError as e:
        print(f"Error during audio playback: {e}")
    except FileNotFoundError:
        print("Error: 'your_audio_file.wav' not found. Please provide a valid path.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def event_catch(ch):
    global play_status, playback_thread

    index = buttonsDict[ch]
    prevIndex = buttonsDict[prevCh]

    if prevCh == 0:
        play_status[index] = True
    elif prevCh == ch:
        play_status[index] = False
    else:
        play_status[index] = True
        play_status[prevIndex] = False
    
    prevCh = ch

    for i in range(len(play_status)):
        GPIO.output(buttons[i][1], play_status[i])
    
    # play_status = not play_status
    # print('Play status: ', play_status)
    # GPIO.output(btn1[1], play_status)
    
    # if play_status:
    #     # Start playback in a new thread
    #     if playback_thread is not None and playback_thread.is_alive():
    #         # If a thread is already running, wait for it to finish (should be quick)
    #         pass
    #     playback_thread = threading.Thread(target=play_audio, daemon=True)
    #     playback_thread.start()
    # else:
    #     # play_status is False, the playback loop will check this and stop
    #     print("Stopping playback...")

for i in range(len(buttons)):
    GPIO.add_event_detect(buttons[i][0], GPIO.FALLING, callback=event_catch, bouncetime=100)

while True:
    pass