from CCT import cct
from CRI import getcri
from Ref_light import reflight
from LER import cal_LER
from xyz import xyz
from phue import Bridge
from fitResult_bri import fitResult_briplux
from fitResult_CCT import fitResult_CCTplux
import requests as rq
import numpy as np
import json
import time
import sys

url_get = 'https://ece4809api.intlightlab.com/get-spectrum-room'
url_post = 'https://ece4809api.intlightlab.com/set-lights'

headers = {'Authorization': 'Bearer 0d90d4d9-ac95-4339-836b-7b733f2973f7'} #special token

target_plux = int(sys.argv[1])

val_bri = fitResult_briplux(target_plux)
val_cct = fitResult_CCTplux(target_plux, val_bri)

input_bri = round(val_bri)
# print('input Bri: ', "{:.2f}".format(input_bri))
input_ct = round(1e6/val_cct)
# print('input CCT: ', "{:.2f}".format(input_ct))

if input_bri > 250:
    input_bri = 250
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

# Calculate CCT from SPM
[x, y, z] = xyz(SPM_interpolated, 1, 2)
measured_CCT = cct(x,y)
ref = reflight(measured_CCT)
[CRI, R9] = getcri(SPM_interpolated, ref)
measured_medi = data["mlux"]
measured_plux = data['plux']
measured_lumen = measured_plux * 19.77
measured_MDER = np.divide(measured_medi, measured_plux)
measured_watt = measured_lumen/measured_LER

# Handle output result
output_data = {
    "Measured CCT": "{:.2f}".format(measured_CCT[0][0]),
    "Measured CRI": "{:.2f}".format(CRI),
    "Measured plux": "{:.2f}".format(measured_plux),
    "Measured medi": "{:.2f}".format(measured_medi),
    "Measured mder": "{:.2f}".format(measured_MDER),
    "Measured LER": "{:.2f}".format(measured_LER),
    "Measured Lumen": "{:.2f}".format(measured_lumen),
    "Measured Watt": "{:.2f}".format(measured_watt),
    "SPM_interpolated": spm_list, 
}
print(json.dumps(output_data))  # Convert the dictionary to JSON and print it
sys.stdout.flush()