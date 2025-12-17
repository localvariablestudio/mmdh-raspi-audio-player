import RPi.GPIO as GPIO
import alsaaudio
import wave
import threading

# Global GPIO config
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
# GPIO.cleanup()

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
    [6, 7],
    [8, 9],
    [10, 11],
    [23, 16]
]

buttonsDict = {
    2 : 0,
    4 : 1,
    6 : 2,
    8 : 3,
    10 : 4,
    23 : 5,
}

tracks = [
    '/home/control-1/Documents/mmdh-raspi-audio-player//media/01-alberto-kurapel.wav',
    '/home/control-1/Documents/mmdh-raspi-audio-player//media/02-isabel-parra.wav',
    '/home/control-1/Documents/mmdh-raspi-audio-player//media/03-mariela-ferreira.wav',
    '/home/control-1/Documents/mmdh-raspi-audio-player//media/04-osvaldo-torres.wav',
    '/home/control-1/Documents/mmdh-raspi-audio-player//media/05-patricio-manns.wav',
    '/home/control-1/Documents/mmdh-raspi-audio-player//media/06-vladimir-vega.wav',
]

for i in range(len(buttons)):
    GPIO.setup(buttons[i][0], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(buttons[i][1], GPIO.OUT, initial=GPIO.LOW)    

def play_audio(index):
    """Play audio in a separate thread, checking play_status periodically"""
    global play_status
    try:
        # Open the WAV file using the index to select the track
        f = wave.open(tracks[index], 'rb') 

        # Initialize a PCM device for playback
        # 'default' refers to the default sound card and device
        # You can specify a different device using 'hw:CARD=0,DEV=0' format
        out = alsaaudio.PCM(channels=f.getnchannels(), rate=f.getframerate(), format=alsaaudio.PCM_FORMAT_S16_LE, periodsize=1024, device='default')

        # Play the audio data
        data = f.readframes(1024)
        while data and play_status[index]:  # Check play_status[index] in the loop
            out.write(data)
            data = f.readframes(1024)
        
        # Clean up if playback was stopped
        if not play_status[index]:
            print("Playback stopped by user")
        
        # On play end
        play_status[index] = False
        print(play_status)
        GPIO.output(buttons[index][1], play_status[index])

        f.close()
        out.close()

    except alsaaudio.ALSAAudioError as e:
        print(f"Error during audio playback: {e}")
    except FileNotFoundError:
        print("Error: 'your_audio_file.wav' not found. Please provide a valid path.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def event_catch(ch):
    global play_status, playback_thread, prevCh
    print(ch)

    index = buttonsDict[ch]
    if prevCh == 0:
        play_status[index] = True
    elif prevCh == ch:
        play_status[index] = not play_status[index]
    else:
        prevIndex = buttonsDict[prevCh]
        play_status[index] = True
        play_status[prevIndex] = False
    
    prevCh = ch

    print(play_status)

    for i in range(len(play_status)):
        GPIO.output(buttons[i][1], play_status[i])
    
    if play_status[index]:
        # Start playback in a new thread
        if playback_thread is not None and playback_thread.is_alive():
            # If a thread is already running, wait for it to finish (should be quick)
            pass
        playback_thread = threading.Thread(target=play_audio, args=(index,), daemon=True)
        playback_thread.start()
    else:
        # play_status is False, the playback loop will check this and stop
        print("Stopping playback...")

for i in range(len(buttons)):
    GPIO.add_event_detect(buttons[i][0], GPIO.FALLING, callback=event_catch, bouncetime=100)

while True:
    pass