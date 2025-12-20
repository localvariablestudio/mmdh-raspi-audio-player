import RPi.GPIO as GPIO
import alsaaudio
import wave
import threading
import struct
import time
import math

# Global GPIO config
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
# GPIO.cleanup()

# ==================================
# Audio settings
play_status = [
    False,
    False,
    False,
    False,
    False,
    False
]

playback_thread = None  # Track the playback thread
current_playback_device = None  # Track the current playback device
current_playback_index = None  # Track which track is currently playing

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

# Volume control
system_vol = 50
vol_down = 15
vol_up = 14

GPIO.setup(vol_down, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(vol_up, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Define system mixer
def get_mixer():
    try:
        return alsaaudio.Mixer(alsaaudio.mixers[0])
    except alsaaudio.ALSAAudioError:
        print(f"Error: Unable to find mixer control '{mixer_name}'")
        print("Try running 'amixer' in your terminal to list available controls and their names (e.g., 'PCM').")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

mixer = get_mixer()

def set_vol(vol):
    global mixer
    mixer.setvolume(vol)

set_vol(system_vol)

def vol_event_catch(ch):
    global mixer, system_vol
    current_volume_list = int(mixer.getvolume()[0])
    if ch == vol_down:
        system_vol = system_vol - 10
        if system_vol < 10:
            system_vol = 10
    elif ch == vol_up:
        system_vol = system_vol + 10
        if system_vol > 100:
            system_vol = 100
    set_vol(int(100 * math.log10(system_vol / 100)))
    print(current_volume_list)


GPIO.add_event_detect(vol_up, GPIO.FALLING, callback=vol_event_catch, bouncetime=100)
GPIO.add_event_detect(vol_down, GPIO.FALLING, callback=vol_event_catch, bouncetime=100)


def fade_audio_data(data, volume_factor):
    """Apply volume factor to audio data (fade in/out)"""
    if volume_factor >= 1.0:
        return data
    
    # Convert bytes to list of 16-bit signed integers
    samples = struct.unpack('<' + 'h' * (len(data) // 2), data)
    # Apply volume factor
    faded_samples = [int(sample * volume_factor) for sample in samples]
    # Convert back to bytes
    return struct.pack('<' + 'h' * len(faded_samples), *faded_samples)

def play_audio(index):
    """Play audio in a separate thread, checking play_status periodically"""
    global play_status, current_playback_device, current_playback_index
    try:
        # Open the WAV file using the index to select the track
        f = wave.open(tracks[index], 'rb') 

        # Initialize a PCM device for playback
        # 'default' refers to the default sound card and device
        # You can specify a different device using 'hw:CARD=0,DEV=0' format
        out = alsaaudio.PCM(channels=f.getnchannels(), rate=f.getframerate(), format=alsaaudio.PCM_FORMAT_S16_LE, periodsize=1024, device='default')
        
        # Store the current playback device
        current_playback_device = out
        current_playback_index = index
        
        # Variables for fade-out
        fade_start_time = None
        fade_duration = 0.5  # 500ms fade-out
        
        # Play the audio data
        data = f.readframes(1024)
        while data and play_status[index]:  # Check play_status[index] in the loop
            # Check if this track is no longer the current track (new track started)
            # If so, start fading out
            if current_playback_index is not None and current_playback_index != index and fade_start_time is None:
                fade_start_time = time.time()
            
            # Apply fade-out if active
            if fade_start_time is not None:
                elapsed = time.time() - fade_start_time
                if elapsed >= fade_duration:
                    # Fade complete, stop playback
                    break
                volume_factor = 1.0 - (elapsed / fade_duration)
                data = fade_audio_data(data, volume_factor)
            
            out.write(data)
            data = f.readframes(1024)
        
        # Clean up if playback was stopped
        if not play_status[index] or fade_start_time is not None:
            if fade_start_time is not None:
                print(f"Track {index} faded out for smooth transition")
            else:
                print("Playback stopped by user")
        
        # On play end
        play_status[index] = False
        print(play_status)
        GPIO.output(buttons[index][1], play_status[index])

        f.close()
        out.close()
        
        # Clear references if this was the current playback
        if current_playback_device == out:
            current_playback_device = None
            current_playback_index = None

    except alsaaudio.ALSAAudioError as e:
        print(f"Error during audio playback: {e}")
    except FileNotFoundError:
        print("Error: 'your_audio_file.wav' not found. Please provide a valid path.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def event_catch(ch):
    global play_status, playback_thread, prevCh, current_playback_index

    index = buttonsDict[ch]
    if prevCh == 0:
        play_status[index] = True
    elif prevCh == ch:
        play_status[index] = not play_status[index]
    else:
        prevIndex = buttonsDict[prevCh]
        play_status[index] = True
        # When switching tracks, the previous track will detect it's no longer current
        # and start fading out automatically (checked in play_audio loop)
        play_status[prevIndex] = False
    
    prevCh = ch

    # Print new play status and update buttons' LED
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