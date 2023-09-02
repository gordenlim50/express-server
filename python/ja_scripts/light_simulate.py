import datetime as dt
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import csv
import json
import sys
import ast
import time

from relatedFunctions import linear_interpolation, alpha_opic_cal, D_illuminant, reflight, getcri
from relatedFunctions import window_dist, xyz, xyToCCT, getZonesSPD, getActualSPD

# Getting inputs (inputs = [(dk what is this), [indoor daylight spectrum (1 zone)], targetvalues])
pred_spd = sys.argv[1]
target_cct = sys.argv[2]
target_plux = sys.argv[3]
target_medi = sys.argv[4]

# Processing inputs 
pred_spd = ast.literal_eval(pred_spd)
target_cct = float(target_cct)
if not target_medi:
    target_plux = float(target_plux)
    target_lx = target_plux
    select = 1
else:
    target_medi = float(target_medi)
    target_lx = target_medi
    select = 2

target_cri = 80

## 
if target_lx > 0:
    target_spec = D_illuminant(target_cct)
    target_spec = getActualSPD(target_spec, target_lx, select)
    spec_temp = []
    for i in range(len(target_spec)):
        spec_temp.append(target_spec[i]-pred_spd[i])

    required_spec = spec_temp

    # Calculate metrics of the required spectrum
    plux_req, medi_req = alpha_opic_cal(required_spec)
    x_req,y_req,z_req = xyz(required_spec, 2)
    cct_req = xyToCCT(x_req,y_req)
    mder_req = medi_req / plux_req

    #---------------------------------Codes to set for Hue lights in the room----------------------------
    with open('python/ja_scripts/all_metrics_wf_sensor2.csv', 'r') as file1:
        reader = csv.reader(file1)
        hue = list(reader)
        hue = hue[1:]
        for i in range(len(hue)):
            hue[i] = [float(val) for val in hue[i]]

    # search for appropriate inputs of hue from the collected data
    lx_dev = 20
    cct_dev = 150
    for i in range(len(hue)):
        if select == 1:
            ind = 7
            lx_req = plux_req
        elif select == 2:
            ind = 6
            lx_req = medi_req
            
        if hue[i][ind] >= lx_req and hue[i][ind] <= lx_req + lx_dev and hue[i][4] >= target_cri:
            spd_corres = hue[i][9:]
            spd_overall = np.array(spd_corres) + np.array(pred_spd)
            x,y,z = xyz(spd_overall, 2)
            cct_overall = xyToCCT(x,y)
            if cct_overall >= cct_req - cct_dev and cct_overall <= cct_req + cct_dev :
                set_bri = hue[i][0]
                set_ct = hue[i][1]
    
    ## Set Hue lights
    url_get = 'https://ece4809api.intlightlab.com/get-spectrum-room'
    url_post = 'https://ece4809api.intlightlab.com/set-lights'
    headers = {'Authorization': 'Bearer 0d90d4d9-ac95-4339-836b-7b733f2973f7'} #special token
    
    set_light = {
        "bri": set_bri,
        "ct": set_ct
    }
    
    response_post = requests.post(url_post, data=set_light, headers=headers)
    time.sleep(6)
    
    # Get request
    response = requests.get(url_get, headers=headers)
    data = response.json()

    # read measured data
    SPM = data['SPM']
    vector = range(0, len(SPM),5) #1:5:len(SPM)
    SPM_interpolated = []
    for k in range(len(vector)):
        SPM_interpolated.append(SPM[vector[k]])
    SPM_interpolated = np.array(SPM_interpolated)
    SPM_interpolated = np.expand_dims(SPM_interpolated, axis=0)
    spd_measured = SPM_interpolated[0]
    
    # Calculate resultant metrics
    x, y, z = xyz(SPM_interpolated[0], 2)
    cct_measured = xyToCCT(x,y)
    ref = reflight(cct_measured)
    cri_measured, r9 = getcri(SPM_interpolated, ref)
    plux_measured = data['plux']
    medi_measured = data['mlux']
    mder_measured = medi_measured / plux_measured
    

    #---------------------------------------------------------------------------------------------------
else:
    target_spec = [0] * 81
    required_spec = [0] * 81
    spd_measured = pred_spd
    plux_req = 0
    medi_req = 0
    cct_req = 0
    cct_measured = 0
    plux_measured = 0
    medi_measured = 0
    mder_measured = 0
    cri_measured = 0

# processing outputs
outputs_process = [target_spec, required_spec, spd_measured]
for i in range(len(outputs_process)):
    temp1 = np.array(outputs_process[i])
    temp1 = temp1.tolist()
    outputs_process[i] = temp1


# Handle output result
output_data = {
    'required_led_plux': f'{plux_req:.2f}',
    'required_led_medi': f'{medi_req:.2f}',
    'required_led_cct': f'{cct_req:.2f}',
    'resultant_plux': f'{plux_measured:.2f}',
    'resultant_medi': f'{medi_measured:.2f}',
    'resultant_cct': f'{cct_measured:.2f}',
    'resultant_mder': f'{mder_measured:.2f}',
    'resultant_cri': f'{cri_measured:.2f}',
    'target_spectrum': outputs_process[0],
    'required_led_spectrum': outputs_process[1],
    'resultant_spectrum': outputs_process[2]
}
# output_data = {
#     'required_led_spectrum': required_spec,
#     'required_led_plux': f'{plux_req:.2f}',
#     'required_led_medi': f'{medi_req:.2f}',
#     'required_led_cct': f'{cct_req:.2f}'
# }
print(json.dumps(output_data))  # Convert the dictionary to JSON and print it
sys.stdout.flush()