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
target_plux = 180 #int(sys.argv[1])
target1 = target_plux
target_medi = 120 #int(sys.argv[2])
target2 = target_medi
diff1 = 100
diff2 = 100

# Steps Constant
plux_step = 10
medi_step = 10

# Time step Constant
time_step = 2 * 60          # Step 2 minutes
time_allocate = 10 * 60     # Allocate 10 minutes

# Initialize a flag to track whether to adjust targets
adjust_targets = True
start_time = time.time()
total_elapsed_time = 0  # Initialize total elapsed time

print('Target PLUX:', "{:.2f}".format(target1))
print('Target MEDI:', "{:.2f}".format(target2))

while True:
    if adjust_targets:
        print("\nIteration: ", iteration)

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
        print("measured Plux: ", "{:.2f}".format(measured_plux))
        measured_lumen = measured_plux * 19.77
        measured_medi = data['mlux']
        print("measured Plux: ", "{:.2f}".format(measured_medi))
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
    if diff1 < 4 and diff2 < 4:
        iteration = 1 # Reset iteration
        adjust_targets = False  # Set the flag to False to exit the loop

    # Check if it's time to increase CCT and PLUX values
    current_time = time.time()
    elapsed_time = current_time - start_time
    
    if elapsed_time >= time_step:
        # Plux increment
        if((target1 + plux_step) >= 0) and ((target1 + plux_step) <= 250):
            target_plux = target1 + plux_step
            target1 = target_plux
            print('\nTarget PLUX:', "{:.2f}".format(target1))
        else:
            print("Plux target at range of 0lx ~ 250lx.")

        # Medi increment 
        if ((target2 + medi_step) >= 0) and  ((target2 + medi_step)<= 200):
            target_medi = target2 + medi_step
            target2 = target_medi
            print('Target MEDI:', "{:.2f}".format(target2))
        else: 
            print("Medi target at range of 0lx ~ 200lx.")

        # Add elapsed_time to total_elapsed_time
        total_elapsed_time += elapsed_time

        # Reset the start_time to current time
        start_time = time.time()
        elapsed_time = 0  # Reset elapsed_time
        adjust_targets = True  # Set the flag to True to adjust targets in the next iteration
        
    # Check if it's time to stop the program
    if total_elapsed_time >= time_allocate:
        print("Time allocation reached. Stopping the program.")
        break  # Exit the loop and stop the program