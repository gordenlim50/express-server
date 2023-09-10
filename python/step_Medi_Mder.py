from CCT import cct
from CRI import getcri
from Ref_light import reflight
from LER import cal_LER
from xyz import xyz
from phue import Bridge
from fitResult_bri import fitResult_brinvs
from fitResult_CCT import fitResult_CCTnvs
import requests as rq
import numpy as np
import json
import time
import datetime
import sys

url_get = 'https://ece4809api.intlightlab.com/get-spectrum-room'
url_post = 'https://ece4809api.intlightlab.com/set-lights'

headers = {'Authorization': 'Bearer 0d90d4d9-ac95-4339-836b-7b733f2973f7'} #special token

Kp1 = 0.55
Kp2 = 0.05
iteration = 1
error_medi = 1e5
error_mder = 1e5
target_medi = int(sys.argv[2])
target1 = target_medi
target_mder = float(sys.argv[3])
target2 = target_mder
diff1 = 100
diff2 = 10

# Steps Constant
medi_steps = [int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), int(sys.argv[8])]
mder_steps = [int(sys.argv[9]), int(sys.argv[10]), int(sys.argv[11]), int(sys.argv[12]), int(sys.argv[13])]
medi_i = 0
mder_i = 0 

# Time step Constant
time_steps_minutes = [int(sys.argv[14]), int(sys.argv[15]), int(sys.argv[16]), int(sys.argv[17]), int(sys.argv[18]), 5]      # Step in minutes
time_step_i = 0
time_allocate = (int(sys.argv[1])+1) * 60     # Allocate 10 minutes

# Results
Medi_Target = []
Medi_Measured = []
Mder_Target = []
Mder_Measured = []
time_values = []

# Initialize a flag to track whether to adjust targets
adjust_targets = True
start_time = time.time()
Starting_time_p = datetime.datetime.now()
formatted_time1 = Starting_time_p.strftime("%I:%M:%S %p")
time_values.append(formatted_time1)
total_elapsed_time = 0  # Initialize total elapsed time

Medi_Target.append(target1)
Mder_Target.append(target2)

while True:
    # Convert time step from minutes to seconds
    if time_step_i < len(time_steps_minutes):
        time_step = time_steps_minutes[time_step_i] * 60

    # Only adjust targets if the flag is set to True
    if adjust_targets:
      
        val_bri = fitResult_brinvs(target_medi, target_mder)
        val_cct = fitResult_CCTnvs(target_medi, target_mder)

        input_bri = round(val_bri)
        input_ct = round(1e6/val_cct)

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
        ref = reflight(measured_CCT)
        [CRI, R9] = getcri(SPM_interpolated, ref)
        measured_medi = data['mlux']
        measured_plux = data['plux']
        measured_mder = data['mlux']/data['plux']
        measured_lumen = measured_plux * 19.77
        measured_watt = measured_lumen/measured_LER

        diff1 = abs(target1 - measured_medi)
        diff2 = abs(target2 - measured_mder)
        error_medi = measured_medi - target_medi
        error_mder = measured_mder - target_mder

        if diff1 < 10:
            target_medi = target_medi - Kp1*diff1
            target_mder = target_mder - Kp2*diff2
        else:
            target_medi = target_medi - Kp1*error_medi 
            target_mder = target_mder - Kp2*error_mder 

        iteration += 1
        time.sleep(5)

    # Check if both targets are nearly reached
    if (diff1 < 4 and diff2 < 0.05) or iteration == 7:
        iteration = 1 # Reset iteration
        adjust_targets = False  # Set the flag to False to exit the loop
        
    # Check if it's time to increase CCT and PLUX values
    current_time = time.time()
    elapsed_time = current_time - start_time

    if elapsed_time >= time_step:
        if not adjust_targets:
            # Append Medi and Mder
            Medi_Measured.append(f'measured_medi:.2f')
            Mder_Measured.append(f'measured_mder:.2f')

            # Increment the time_step_index to use the next time step in the array
            time_step_i += 1

            # MEDI increment
            if medi_i < len(medi_steps):
                new_target_medi = target1 + medi_steps[medi_i]
                if 0 <= new_target_medi <= 250:
                    target_medi = new_target_medi
                    Medi_Target.append(target_medi)
                    target1 = target_medi
                    medi_i += 1

            # MDER increment 
            if mder_i < len(mder_steps):
                new_target_mder = target2 + mder_steps[mder_i]
                if 0 <= new_target_mder <= 200:
                    target_mder = new_target_mder
                    Mder_Target.append(target_mder)
                    target2 = target_mder
                    current_time = datetime.datetime.now()
                    formatted_time = current_time.strftime("%I:%M:%S %p")
                    time_values.append(formatted_time)
                    mder_i += 1

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
    "Medi_Target": Medi_Target,
    "Mder_Target": Mder_Target,
    "Medi_Measured": Medi_Measured,
    "Mder_Measured": Mder_Measured,
    "Time": time_values
}
print(json.dumps(output_data))  # Convert the dictionary to JSON and print it
sys.stdout.flush()