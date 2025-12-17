import RPi.GPIO as GPIO
import alsaaudio
import wave
import threading
import struct
import time
import sys

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
current_playback_device = None  # Track the current playback device
current_playback_index = None  # Track which track is currently playing
playback_lock = threading.Lock()  # Lock to prevent simultaneous audio device access

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

def fade_audio_data(data, volume_factor):
    """Apply volume factor to audio data (fade in/out)"""
    # Clamp volume_factor to valid range [0.0, 1.0]
    volume_factor = max(0.0, min(1.0, volume_factor))
    
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
    global play_status, current_playback_device, current_playback_index, playback_lock
    try:
        # Check if there's a previous track playing (switching tracks)
        # If so, wait for the fade-out to complete (500ms) plus a small buffer
        fade_duration = 0.5  # 500ms for fade-out
        if current_playback_index is not None and current_playback_index != index:
            # Wait for fade-out to complete - this ensures the previous track has finished
            # and closed its device before we open a new one
            time.sleep(fade_duration + 0.15)  # Wait for fade-out (500ms) + buffer (150ms)
        
        # Open the WAV file using the index to select the track
        f = wave.open(tracks[index], 'rb') 

        # Initialize a PCM device for playback with lock to prevent conflicts
        with playback_lock:
            # 'default' refers to the default sound card and device
            # You can specify a different device using 'hw:CARD=0,DEV=0' format
            out = alsaaudio.PCM(channels=f.getnchannels(), rate=f.getframerate(), format=alsaaudio.PCM_FORMAT_S16_LE, periodsize=1024, device='default')
            
            # Store the current playback device
            current_playback_device = out
            current_playback_index = index
        
        # Variables for fade-in and fade-out
        fade_in_start_time = time.time()  # Start fade-in immediately
        fade_out_start_time = None
        fade_duration = 0.5  # 500ms for both fade-in and fade-out
        
        # Progress bar variables
        total_frames = f.getnframes()
        frames_read = 0
        frame_size = 1024  # Number of frames read per iteration
        sample_rate = f.getframerate()
        last_progress_update = time.time()
        progress_update_interval = 0.5  # Update progress bar every 0.5 seconds
        
        # Play the audio data
        data = f.readframes(1024)
        while data and play_status[index]:  # Check play_status[index] in the loop
            # Check if this track is no longer the current track (new track started)
            # If so, start fading out
            if current_playback_index is not None and current_playback_index != index and fade_out_start_time is None:
                fade_out_start_time = time.time()
            
            # Determine which fade to apply
            volume_factor = 1.0
            
            # Apply fade-out if active (takes priority over fade-in)
            if fade_out_start_time is not None:
                elapsed = time.time() - fade_out_start_time
                if elapsed >= fade_duration:
                    # Fade complete, stop playback
                    break
                volume_factor = 1.0 - (elapsed / fade_duration)
            # Apply fade-in if active and not fading out
            elif fade_in_start_time is not None:
                elapsed = time.time() - fade_in_start_time
                if elapsed < fade_duration:
                    # Still fading in
                    volume_factor = elapsed / fade_duration
                else:
                    # Fade-in complete
                    fade_in_start_time = None
                    volume_factor = 1.0
            
            # Apply volume factor to audio data
            if volume_factor < 1.0:
                data = fade_audio_data(data, volume_factor)
            
            # Check if we're still the current track before writing (quick check without lock)
            # If not current, the fade-out logic above will handle handling stopping
            try:
                out.write(data)
            except (OSError, alsaaudio.ALSAAudioError):
                # Device may have been closed by another thread, break out of loop
                break
            
            # Update progress tracking
            # Calculate actual frames read from data length
            bytes_per_frame = f.getsampwidth() * f.getnchannels()
            frames_in_data = len(data) // bytes_per_frame if bytes_per_frame > 0 else 0
            frames_read += frames_in_data
            current_time = time.time()
            
            # Update progress bar periodically
            if current_time - last_progress_update >= progress_update_interval:
                progress = min(frames_read / total_frames, 1.0) if total_frames > 0 else 0.0
                current_seconds = frames_read / sample_rate if sample_rate > 0 else 0
                total_seconds = total_frames / sample_rate if sample_rate > 0 else 0
                
                # Create progress bar (40 characters wide)
                bar_width = 40
                filled = int(bar_width * progress)
                bar = '=' * filled + '-' * (bar_width - filled)
                percentage = int(progress * 100)
                
                # Format time display
                current_min = int(current_seconds // 60)
                current_sec = int(current_seconds % 60)
                total_min = int(total_seconds // 60)
                total_sec = int(total_seconds % 60)
                
                # Print progress bar (using \r to overwrite the same line)
                progress_str = f"Track {index + 1} [{bar}] {percentage}% ({current_min:02d}:{current_sec:02d}/{total_min:02d}:{total_sec:02d})"
                sys.stdout.write('\r' + progress_str)
                sys.stdout.flush()
                
                last_progress_update = current_time
            
            data = f.readframes(1024)
        
        # Print newline to complete progress bar line
        sys.stdout.write('\n')
        sys.stdout.flush()
        
        # Clean up if playback was stopped
        if not play_status[index] or fade_out_start_time is not None:
            if fade_out_start_time is not None:
                print(f"Track {index} faded out for smooth transition")
            else:
                print("Playback stopped by user")
        
        # On play end
        play_status[index] = False
        print(play_status)
        GPIO.output(buttons[index][1], play_status[index])

        f.close()
        
        # Close device and clear references with lock
        with playback_lock:
            try:
                out.close()
            except:
                pass
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