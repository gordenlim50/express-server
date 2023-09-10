import random
import librosa
import numpy as np
import sounddevice as sd
import time
import matplotlib.pyplot as plt
from phue import Bridge
import sys

def rgb_to_xy(red, green, blue):
    # Normalize RGB values
    r = red / 255
    g = green / 255
    b = blue / 255

    # Apply gamma correction
    r = r if r <= 0.04045 else ((r + 0.055) / 1.055) ** 2.4
    g = g if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
    b = b if b <= 0.04045 else ((b + 0.055) / 1.055) ** 2.4

    # Convert RGB to XYZ
    x = r * 0.649926 + g * 0.103455 + b * 0.197109
    y = r * 0.234327 + g * 0.743075 + b * 0.022598
    z = g * 0.053077 + b * 1.035763

    # Convert XYZ to XY
    x_sum = x + y + z
    if x_sum > 0:
        xy = [round(x / x_sum, 4), round(y / x_sum, 4)]
    else:
        xy = [0, 0]

    return xy

b = Bridge('59.191.204.143')

username = b.connect()
b.get_api()

# Get all lights
lights = b.get_light_objects('id')

# Set up colors
COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

# Load the disco music
music = int(sys.argv[1])

if music == "0":
    music_file = "calmdown.mp3"
elif music == "1":
    music_file = "idol_YOASOBI.mp3"

y, sr = librosa.load(music_file)

# Detect beats in the music
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=3250)
# Calculate the time interval between high beats
beat_interval = 60.0 / (tempo+450)

# Play the disco music
sd.play(y, sr)

# Main loop
beat_index = 0
running = True
start_time = time.time()
prev_color = (0, 0, 0)
flag = 0
cnt = 0

index_thres = 0

while running:
    '''
    if flag == 0:
        beat_interval = beat_interval = 60.0 / (tempo+450)
        flag+=1
    elif flag == 1:
        beat_interval = beat_interval = 60.0 / (tempo-100)
        flag-=1
    '''
    current_time = time.time() - start_time
    # print(beat_index)
    if beat_index < len(beats) and current_time >= beats[beat_index] * beat_interval:
        if beat_index >= index_thres:
            cnt+=1
            if cnt == 2 or cnt == 0:
                beat_index+=1
            else:
                current_color = random.choice(COLORS)
                while prev_color == current_color:
                    current_color = random.choice(COLORS)
                #print("Current color:", current_color)
                
                # set light color
                xy = rgb_to_xy(current_color[0], current_color[1], current_color[2])
                b.set_light(lights, {'xy': xy})
                
                prev_color = current_color
                beat_index += 1
        
            if cnt == 4:
                cnt = 0
        else:
            beat_index += 1

    # Delay to synchronize with music
    time.sleep(0.01)  # Adjust the delay as needed

    # Stop the program when the music ends
    if beat_index >= len(beats):
        running = False

# End of program
