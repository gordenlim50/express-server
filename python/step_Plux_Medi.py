from CCT import cct
from CRI import getcri
from Ref_light import reflight
from LER import cal_LER
from xyz import xyz
from phue import Bridge
from fitResult_bri import fitResult_bri_pm
from fitResult_CCT import fitResult_CCT_pm
import requests as rq
import numpy as np
import json
import time
import sys

# API links
url_get = 'https://ece4809api.intlightlab.com/get-spectrum-room'
url_post = 'https://ece4809api.intlightlab.com/set-lights'

headers = {'Authorization': 'Bearer 0d90d4d9-ac95-4339-836b-7b733f2973f7'} #special token

# Initialize variables for time tracking
# Controller Constant
Kp_plux = 0.6
Kp_medi = 0.5
iteration = 1
error_plux = 1e5
error_medi = 1e5
target_plux = int(sys.argv[2])
target1 = target_plux
target_medi = int(sys.argv[3])
target2 = target_medi
diff1 = 100
diff2 = 100

# Steps Constant
plux_steps = [int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), int(sys.argv[8])]
medi_steps = [int(sys.argv[9]), int(sys.argv[10]), int(sys.argv[11]), int(sys.argv[12]), int(sys.argv[13])]
plux_i = 0
medi_i = 0

# Time step Constant
time_steps_minutes = [int(sys.argv[14]), int(sys.argv[15]), int(sys.argv[16]), int(sys.argv[17]), int(sys.argv[18]), 5]       # Step in minutes
time_step_i = 0
time_allocate = int(sys.argv[1]) * 60                 # Allocate 10 minutes

# Results
Plux_Target = []
Plux_Measured = []
Medi_Target = []
Medi_Measured = []

# Initialize a flag to track whether to adjust targets
adjust_targets = True
start_time = time.time()
total_elapsed_time = 0  # Initialize total elapsed time

Plux_Target.append(target1)
Medi_Target.append(target2)

while True:
    # Convert time step from minutes to seconds
    if time_step_i < len(time_steps_minutes):
        time_step = time_steps_minutes[time_step_i] * 60

    # Only adjust targets if the flag is set to True
    if adjust_targets:
       
        val_bri = fitResult_bri_pm(target_plux, target_medi)
        val_cct = fitResult_CCT_pm(target_plux, target_medi)

        input_bri = val_bri
        input_ct = 1e6/val_cct

        if input_bri > 250:
            input_bri = 254
        elif input_bri < 0:
            input_bri = 0
        
        if input_ct > 500:
            input_ct = 500
        elif input_ct < 154:
            input_ct = 154
        
        # Post request
        set_light = {
            "bri": input_bri,
            "ct": input_ct
        }
        response_post = rq.post(url_post, data=set_light, headers = headers)
        
        time.sleep(10)

        # Get request
        response = rq.get(url_get, headers = headers)
        data = response.json()
        #Read SPM
        SPM = data['SPM']
        vector = range(0, len(SPM),5) #1:5:len(SPM)
        SPM_interpolated = []
        for i in range(len(vector)):
            SPM_interpolated.append(SPM[vector[i]])

        SPM_interpolated = np.array(SPM_interpolated)
        SPM_interpolated = np.expand_dims(SPM_interpolated, axis=0)
        spm_i = SPM_interpolated[0]
        spm_list = spm_i.tolist()
    
        measured_LER = cal_LER(spm_i)

        # Calculate CCT and CRI from SPM
        [x, y, z] = xyz(SPM_interpolated, 1, 2)
        measured_CCT = cct(x,y)
        ref = reflight(measured_CCT)
        [CRI, R9] = getcri(SPM_interpolated, ref)

        measured_plux = data['plux']
        measured_lumen = measured_plux * 19.77
        measured_medi = data['mlux']
        measured_mder = data['mlux']/data['plux']
        measured_watt = measured_lumen/measured_LER

        diff1 = abs(target1 - measured_plux)
        diff2 = abs(target2 - measured_medi)
        diff3 = measured_plux - target1
        diff4 = measured_medi - target2
        error_plux = measured_plux - target_plux
        error_medi = measured_medi - target_medi

        if diff1 < 20 or diff2 < 20:
            target_plux = target_plux - Kp_plux*diff3
            target_medi = target_medi - Kp_medi*diff4
        else:
            target_plux = target_plux - Kp_plux*error_plux
            target_medi = target_medi - Kp_medi*error_medi 
        
        iteration += 1
        time.sleep(5)

    # Check if both targets are nearly reached
    if (diff1 < 4 and diff2 < 4) or iteration == 7:
        iteration = 1 # Reset iteration
        adjust_targets = False  # Set the flag to False to exit the loop

    # Check if it's time to increase CCT and PLUX values
    current_time = time.time()
    elapsed_time = current_time - start_time
    
    if elapsed_time >= time_step:
        # Plux and Medi
        Plux_Measured.append(f'{measured_CCT[0][0]:.2f}')
        Medi_Measured.append(f'{measured_medi:.2f}')

        # Increment the time_step_index to use the next time step in the array
        time_step_i += 1

        # Plux increment
        if plux_i < len(plux_steps):
            new_target_plux = target1 + plux_steps[plux_i]
            if 0 <= new_target_plux <= 250:
                target_plux = new_target_plux
                Plux_Target.append(target_plux)
                target1 = target_plux
                plux_i += 1

        # Medi increment 
        if medi_i < len(medi_steps):
            new_target_medi = target2 + medi_steps[medi_i]
            if 0 <= new_target_medi <= 200:
                target_medi = new_target_medi
                Medi_Target.append(target_medi)
                target2 = target_medi
                medi_i += 1

        # Add elapsed_time to total_elapsed_time
        total_elapsed_time += elapsed_time

        # Reset the start_time to current time
        start_time = time.time()
        elapsed_time = 0  # Reset elapsed_time
        adjust_targets = True  # Set the flag to True to adjust targets in the next iteration
        
    # Check if it's time to stop the program
    if total_elapsed_time >= time_allocate:
        break  # Exit the loop and stop the program

# Handle output result
output_data = {
    "Plux_Target": Plux_Target,
    "Medi_Target": Medi_Target,
    "Plux_Measured": Plux_Measured,
    "Medi_Measured": Medi_Measured
}
print(json.dumps(output_data))  # Convert the dictionary to JSON and print it
sys.stdout.flush()