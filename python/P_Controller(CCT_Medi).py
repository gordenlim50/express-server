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
target_medi = int(sys.argv[2])
target1 = target_medi
target_cct = int(sys.argv[1])
target2 = target_cct
diff1 = 100
diff2 = 100

while diff1 > 5 or diff2 > 50:
   
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
    ref = reflight(measured_CCT)
    [CRI, R9] = getcri(SPM_interpolated, ref)

    measured_plux = data['plux']
    measured_lumen = measured_plux * 19.77
    measured_medi = data['mlux']
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
    if iteration == 6:
        break

# Handle output result
output_data = {
    "Measured CCT": "{:.2f}".format(measured_CCT[0][0]),
    "Measured CRI": "{:.2f}".format(CRI),
    "Measured plux": "{:.2f}".format(measured_plux),
    "Measured medi": "{:.2f}".format(measured_medi),
    "Measured mder": "{:.2f}".format(measured_mder),
    "Measured LER": "{:.2f}".format(measured_LER),
    "Measured Lumen": "{:.2f}".format(measured_lumen),
    "Measured Watt": "{:.2f}".format(measured_watt),
    "SPM_interpolated": spm_list, 
}
print(json.dumps(output_data))  # Convert the dictionary to JSON and print it
sys.stdout.flush()