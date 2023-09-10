from CCT import cct
from CRI import getcri
from Ref_light import reflight
from LER import cal_LER
from xyz import xyz
from phue import Bridge
from fitResult_bri import fitResult_bri_cm
import requests as rq
import numpy as np
import json
import time
import sys

url_get = 'https://ece4809api.intlightlab.com/get-spectrum-room'
url_post = 'https://ece4809api.intlightlab.com/set-lights'

headers = {'Authorization': 'Bearer 0d90d4d9-ac95-4339-836b-7b733f2973f7'} #special token

Kp_medi = 0.6
Kp_cct = 0.6 
iteration = 1
error_medi = 1e5
error_cct = 1e5
target_medi = int(sys.argv[3])
target1 = target_medi
target_cct = int(sys.argv[2])
target2 = target_cct
diff1 = 100
diff2 = 100

# Steps Constant
cct_steps = [int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), int(sys.argv[8])]
medi_steps = [int(sys.argv[9]), int(sys.argv[10]), int(sys.argv[11]), int(sys.argv[12]), int(sys.argv[13])]
cct_i = 0
medi_i = 0

# Time step Constant
time_steps_minutes = [int(sys.argv[14]), int(sys.argv[15]), int(sys.argv[16]), int(sys.argv[17]), int(sys.argv[18]), 5]       # Step 2 minutes
time_step_i = 0
time_allocate = int(sys.argv[1]) * 60                 # Allocate 10 minutes

# Results
CCT_Target = []
CCT_Measured = []
Medi_Target = []
Medi_Measured = []

# Initialize a flag to track whether to adjust targets
adjust_targets = True
start_time = time.time()
total_elapsed_time = 0  # Initialize total elapsed time

# print('Target CCT:', "{:.2f}".format(target2))
CCT_Target.append(target2)
# print('Target MEDI:', "{:.2f}".format(target1))
Medi_Target.append(target1)

while True:

    # Convert time step from minutes to seconds
    time_step = time_steps_minutes[time_step_i] * 60

    # Only adjust targets if the flag is set to True
    if adjust_targets:
        # print("\nIteration: ", iteration)

        val_bri = fitResult_bri_cm(target_medi, target_cct)
        val_cct = target_cct

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
        response_post = rq.post(url_post, data=set_light, headers=headers)
        
        time.sleep(10)

        # Get request
        response = rq.get(url_get, headers=headers)
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
        # print("measured CCT: ", "{:.2f}".format(measured_CCT[0][0]))
        ref = reflight(measured_CCT)
        [CRI, R9] = getcri(SPM_interpolated, ref)

        measured_plux = data['plux']
        measured_lumen = measured_plux * 19.77
        measured_medi = data['mlux']
        # print("measured MEDI: ", "{:.2f}".format(measured_medi))
        measured_mder = data['mlux']/data['plux']
        measured_watt = measured_lumen/measured_LER

        diff1 = abs(target1 - measured_medi)
        diff2 = abs(target2 - measured_CCT)
        diff3 = measured_medi - target1
        diff4 = measured_CCT - target2
        error_medi = measured_medi - target_medi
        error_cct = measured_CCT - target_cct
        

        if diff1 < 20 or diff2 < 200:
            target_medi = target_medi - Kp_medi*diff3
            target_cct = target_cct - Kp_cct*diff4
        else:
            target_medi = target_medi - Kp_medi*error_medi
            target_cct = target_cct - Kp_cct*error_cct 

        iteration += 1
        time.sleep(5)
        

    # Check if both targets are nearly reached
    if (diff1 < 4 and diff2 < 50) or iteration == 7:
        iteration = 1 # Reset iteration
        adjust_targets = False  # Set the flag to False to exit the loop
       
        
    # Check if it's time to increase CCT and PLUX values
    current_time = time.time()
    elapsed_time = current_time - start_time

    if elapsed_time >= time_step:
        CCT_Measured.append(f'measured_CCT[0][0]:.2f')
        Medi_Measured.append(f'measured_medi:.2f')

        # Increment the time_step_index to use the next time step in the array
        time_step_i += 1

        # CCT increment 
        if cct_i < len(cct_steps):
            new_target_cct = target2 + cct_steps[cct_i]
            if 2500 <= new_target_cct <= 6500:
                target_cct = new_target_cct
                CCT_Target.append(target_cct)
                target2 = target_cct
                cct_i += 1
        
        # Plux increment
        if medi_i < len(medi_steps):
            new_target_medi  = target1 + medi_steps[medi_i]
            if 0 <= new_target_medi <= 200:
                target_medi = new_target_medi
                Medi_Target.append(target_medi)
                target1 = target_medi
                medi_i += 1
                
        # Add elapsed_time to total_elapsed_time
        total_elapsed_time += elapsed_time

        # Reset the start_time to current time
        start_time = time.time()
        elapsed_time = 0  # Reset elapsed_time
        adjust_targets = True  # Set the flag to True to adjust targets in the next iteration
        
         # Check if both targets are nearly reached and append the measurements for this iteration
  
    # Check if it's time to stop the program
    if total_elapsed_time >= time_allocate:
        break  # Exit the loop and stop the program

# Handle output result
output_data = {
    "CCT_Target": CCT_Target,
    "Medi_Target": Medi_Target,
    "CCT_Measured": CCT_Measured,
    "Medi_Measured": Medi_Measured,
}
print(json.dumps(output_data))  # Convert the dictionary to JSON and print it
sys.stdout.flush()