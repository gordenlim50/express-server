import requests as rq
import json
import matplotlib.pyplot as plt
import numpy as np
import math
from relatedFunctions import cal_LER, xyToCCT, xyz, reflight, getcri
import time
from datetime import datetime
import pandas as pd
import sched
import subprocess
import sys

def task():

    url_get = 'https://ece4809api.intlightlab.com/get-spectrum-room'
    url_post = 'https://ece4809api.intlightlab.com/set-lights'

    headers = {'Authorization': 'Bearer 0d90d4d9-ac95-4339-836b-7b733f2973f7'} #special token

    reader = pd.read_excel('python/calibration_data.xlsx')

    i = 0
    ccts = np.arange(int(sys.argv[4]), int(sys.argv[5])+1, int(sys.argv[6]))
    ccts = ccts.tolist()
    bris = np.arange(int(sys.argv[1]), int(sys.argv[2])+1, int(sys.argv[3]))
    bris = np.append(bris, [254])
    iter = 0

    while i < len(bris):
        j = 0
        bri_light = bris[i]

        while j < len(ccts):
            cct_light = ccts[j]
            
            ct = 1e6/ cct_light

            set_light = {
                "bri":  bri_light,
                "ct": ct
            }

            response_post = rq.post(url_post, data=set_light, headers=headers)
           
            time.sleep(15)

            # Get request
            response = rq.get(url_get, headers=headers)
            data = response.json()
            #Read SPM
            SPM = data['SPM']
            vector = range(0, len(SPM),5) #1:5:len(SPM)
            SPM_interpolated = []
            for k in range(len(vector)):
                SPM_interpolated.append(SPM[vector[k]])

            SPM_interpolated = np.array(SPM_interpolated)
            SPM_interpolated = np.expand_dims(SPM_interpolated, axis=0)
            SPM = SPM_interpolated[0]
        
            LER = cal_LER(SPM)

            # Calculate CCT and CRI from SPM
            x, y, z = xyz(SPM_interpolated[0], 2)
            CCT = xyToCCT(x,y)
            ref = reflight(CCT)
            [CRI, R9] = getcri(SPM_interpolated, ref)

            PLUX = data['plux']
            MLUX = data['mlux']
            MDER = data['mlux']/data['plux']

            spm = SPM
            data1 = [iter, bri_light, ct, cct_light, CCT, CRI, LER, MLUX, PLUX, MDER, *spm]

            # Append data to excel file
            df = pd.DataFrame(data1)
            reader = pd.read_excel('python/calibration_data.xlsx')
            writer = pd.ExcelWriter('python/calibration_data.xlsx', engine='openpyxl', mode='a', if_sheet_exists="overlay")
            df.to_excel(writer, index=False, header=False, startcol=len(reader.columns))
            writer.close()

            j += 1
            iter += 1
        i += 1

    # Handle output result
    output_data = {
        "bri": bri_light,
        "cct": cct_light,

    }
    print(json.dumps(output_data))
    sys.stdout.flush()
    

current_time = time.time()
scheduler = sched.scheduler(time.time, time.sleep)
minutes = 0.5
delay_seconds = minutes*60

while 1:
    # Creates an instance of the scheduler class
    scheduler = sched.scheduler(time.time, time.sleep)

    scheduler.enterabs(current_time+delay_seconds, 1, task)

    # Run all scheduled events
    scheduler.run()

    # update current time
    current_time = time.time()

