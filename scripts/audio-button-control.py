import RPi.GPIO as GPIO
import alsaaudio
import wave

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
    # Example for playing a WAV file
    try:
        # Open the WAV file
        f = wave.open('../assets/audio-test.wav', 'rb') 

        # Initialize a PCM device for playback
        # 'default' refers to the default sound card and device
        # You can specify a different device using 'hw:CARD=0,DEV=0' format
        out = alsaaudio.PCM(channels=f.getnchannels(), rate=f.getframerate(), format=alsaaudio.PCM_FORMAT_S16_LE, periodsize=1024, device='default')

        # Play the audio data
        data = f.readframes(1024)
        while data:
            out.write(data)
            data = f.readframes(1024)

        f.close()
        out.close()

    except alsaaudio.ALSAAudioError as e:
        print(f"Error during audio playback: {e}")
    except FileNotFoundError:
        print("Error: 'your_audio_file.wav' not found. Please provide a valid path.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

GPIO.add_event_detect(btn1[0], GPIO.FALLING, callback=event_catch, bouncetime=100)

while True:
    pass