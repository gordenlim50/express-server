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
from relatedFunctions import window_dist, xyz, xyToCCT, getZonesSPD, getActualSPD, fitResult_bri_cm, fitResult_bri_cp

import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.preprocessing import StandardScaler

from torchmetrics import Accuracy, MeanSquaredError

from pytorch_lightning.callbacks import EarlyStopping
from pytorch_lightning import LightningModule, Trainer, seed_everything
from pytorch_lightning.callbacks.progress import TQDMProgressBar
from pytorch_lightning.loggers import CSVLogger
from pytorch_lightning.callbacks import Callback, ModelCheckpoint

url_get = 'https://ece4809api.intlightlab.com/get-spectrum-room'
url_post = 'https://ece4809api.intlightlab.com/set-lights'
headers = {'Authorization': 'Bearer 0d90d4d9-ac95-4339-836b-7b733f2973f7'} #special token

class HueLights(LightningModule):
    def __init__(self, input_dim=4, hidden_dim=512, output_dim=2, learning_rate=1e-5, dropout_prob=0.25):
        super().__init__()
        
        self.learning_rate = learning_rate
        self.criterion = nn.MSELoss()
        
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        
        self.fc2 = nn.Linear(hidden_dim, hidden_dim//2)
        self.fc3 = nn.Linear(hidden_dim//2, hidden_dim//4)
#         self.fc4 = nn.Linear(hidden_dim//2, hidden_dim//4)
        
        self.dropout1 = nn.Dropout(p=dropout_prob)
        self.dropout2 = nn.Dropout(p=dropout_prob)
        self.dropout3 = nn.Dropout(p=dropout_prob)
#         self.dropout4 = nn.Dropout(p=dropout_prob)
        
        self.fc4 = nn.Linear(hidden_dim//4, output_dim)
        
        self.train_mse = MeanSquaredError()
        self.val_mse = MeanSquaredError()
        self.test_mse = MeanSquaredError()
        
    def forward(self, x):
        x = x.to(self.fc1.weight.dtype)

        x = F.relu(self.fc1(x))
        x = self.dropout1(x)
        x = F.relu(self.fc2(x))
        x = self.dropout2(x)
        x = F.relu(self.fc3(x))
        x = self.dropout3(x)
#         x = F.relu(self.fc4(x))
#         x = self.dropout4(x)
        
        x = self.fc4(x)

        return x
        
    def training_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        loss = self.criterion(y_hat, y)
        self.train_mse.update(y_hat, y)
        
        self.log('train_loss', loss, prog_bar=True, on_step=False, on_epoch=True)
        self.log('train_mse', self.train_mse, prog_bar=True, on_step=False, on_epoch=True)
        
        return loss
    
    def validation_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        loss = self.criterion(y_hat, y)
        self.val_mse.update(y_hat, y)
        
        self.log('val_loss', loss, prog_bar=True, on_epoch=True)
        self.log('val_mse', self.val_mse, prog_bar=True, on_epoch=True)
        
        return y_hat
    
    def test_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        loss = self.criterion(y_hat, y)
        self.test_mse.update(y_hat, y)
        
        self.log('test_loss', loss, prog_bar=True)
        self.log('test_mse', self.test_mse, prog_bar=True)
        
        return y_hat
    
    def predict_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        
        return y_hat, x, y
    
    def configure_optimizers(self):
        optimizer = torch.optim.AdamW(self.parameters(), lr=self.learning_rate)
        return optimizer

class RoomRadiancePredictor(LightningModule):
    def __init__(self, input_dim=2, hidden_dim=64, output_dim=2, learning_rate=1e-3):
        super().__init__()
        
        self.learning_rate = learning_rate
        self.criterion = nn.MSELoss()
        
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, hidden_dim)
        self.fc4 = nn.Linear(hidden_dim, hidden_dim)
        
        self.fc5 = nn.Linear(hidden_dim, output_dim)
        
        self.train_mse = MeanSquaredError()
        self.val_mse = MeanSquaredError()
        self.test_mse = MeanSquaredError()
        
    def forward(self, x):
        x = x.to(self.fc1.weight.dtype)

        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = F.relu(self.fc4(x))
        x = self.fc5(x)

        return x
        
    def training_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        loss = self.criterion(y_hat, y)
        self.train_mse.update(y_hat, y)
        
        self.log('train_loss', loss, prog_bar=True, on_step=False, on_epoch=True)
        self.log('train_mse', self.train_mse, prog_bar=True, on_step=False, on_epoch=True)
        
        return loss
    
    def validation_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        loss = self.criterion(y_hat, y)
        self.val_mse.update(y_hat, y)
        
        self.log('val_loss', loss, prog_bar=True, on_epoch=True)
        self.log('val_mse', self.val_mse, prog_bar=True, on_epoch=True)
        
        return y_hat
    
    def test_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        loss = self.criterion(y_hat, y)
        self.test_mse.update(y_hat, y)
        
        self.log('test_loss', loss, prog_bar=True)
        self.log('test_mse', self.test_mse, prog_bar=True)
        
        return y_hat
    
    def predict_step(self, batch, batch_idx):
        x, y = batch
        y_hat = self(x)
        
        return y_hat, x, y
    
    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=self.learning_rate)
        return optimizer
    
    ####################
    # DATA RELATED HOOKS
    ####################

# Getting inputs (inputs = [(dk what is this), [indoor daylight spectrum (1 zone)], targetvalues])
pred_spd = sys.argv[1]
target_cct = sys.argv[2]
target_plux = sys.argv[3]
target_medi = sys.argv[4]

# Processing inputs 
pred_spd = ast.literal_eval(pred_spd)

##
# response = requests.get(url_get, headers=headers)
# data = response.json()
# # read measured data
# pred_spd= data['SPM']
# pred_spd = pred_spd[::5]


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
lights_required = 1
## 
if target_lx > 0:
    plux_daylight, medi_daylight = alpha_opic_cal(pred_spd)
    if plux_daylight >= target_lx and select == 1:
        lights_required = 0
    elif medi_daylight >= target_lx and select == 2:
        lights_required = 0
    
    if lights_required:
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
        # with open('python/ja_scripts/all_metrics_wf_sensor2.csv', 'r') as file1:
        #     reader = csv.reader(file1)
        #     hue = list(reader)
        #     hue = hue[1:]
        #     for i in range(len(hue)):
        #         hue[i] = [float(val) for val in hue[i]]

        # # search for appropriate inputs of hue from the collected data
        # lx_dev = 20
        # cct_dev = 150
        # for i in range(len(hue)):
        #     if select == 1:
        #         ind = 7
        #         lx_req = plux_req
        #     elif select == 2:
        #         ind = 6
        #         lx_req = medi_req
                
        #     if hue[i][ind] >= lx_req and hue[i][ind] <= lx_req + lx_dev and hue[i][4] >= target_cri:
        #         spd_corres = hue[i][9:]
        #         spd_overall = np.array(spd_corres) + np.array(pred_spd)
        #         x,y,z = xyz(spd_overall, 2)
        #         cct_overall = xyToCCT(x,y)
        #         if cct_overall >= cct_req - cct_dev and cct_overall <= cct_req + cct_dev :
        #             set_bri = hue[i][0]
        #             set_ct = hue[i][1]
        
        
        # if select == 2:
        #     set_bri = fitResult_bri_cm(medi_req, cct_req)
        #     set_cct = cct_req
        #     set_ct = 1e6 / set_cct
        # elif select == 1:
        #     set_bri = fitResult_bri_cp(plux_req, cct_req)
        #     set_cct = cct_req
        #     set_ct = 1e6 / set_cct
        
        # # model predictions
        # if select == 2:
        #     plux_req = 0
        # elif select == 1:
        #     medi_req = 0
        
        # model = HueLights.load_from_checkpoint('python/ja_scripts/hue_model_best_300.ckpt')

        # # Set the model to evaluation mode
        # model = model.to('cuda')
        # model.eval()

        # # model inputs
        # model_input = np.array([cct_req, plux_req, medi_req, target_cri])
        # scale_values = np.array([1160.96569466,  122.25173116,   81.09854713,   16.51505755])
        # mean_values = np.array([4080.11539348,  136.80662954,   85.84847745,   79.40112052])
        # scaled_input = (model_input - mean_values)/ scale_values

        # input_data = torch.tensor(scaled_input, dtype=torch.float32)

        # # Pass the input data through the model to obtain predictions
        # with torch.no_grad():
        #     predictions = model(input_data.to('cuda'))
                
        # # Process the predictions
        # predictions = predictions.tolist()
        
        # model predictions
        if select == 2:
            model = RoomRadiancePredictor.load_from_checkpoint('python/ja_scripts/hue_model_411.ckpt')
            # Set the model to evaluation mode
            model = model.to('cuda')
            model.eval()

            # model inputs
            model_input = np.array([cct_req, medi_req])
            scale_values = np.array([1160.96569466, 81.09854713])
            mean_values = np.array([4080.11539348, 85.84847745])
            scaled_input = (model_input - mean_values)/ scale_values

            input_data = torch.tensor(scaled_input, dtype=torch.float32)

            # Pass the input data through the model to obtain predictions
            with torch.no_grad():
                predictions = model(input_data.to('cuda'))
                
            # Process the predictions
            predictions = predictions.tolist()
            
        elif select == 1:
            model = RoomRadiancePredictor.load_from_checkpoint('python/ja_scripts/hue_model_396_plux.ckpt')
            # Set the model to evaluation mode
            model = model.to('cuda')
            model.eval()

            # model inputs
            model_input = np.array([cct_req, plux_req])
            scale_values = np.array([1160.96569466,  122.25173116])
            mean_values = np.array([4080.11539348,  136.80662954])
            scaled_input = (model_input - mean_values)/ scale_values

            input_data = torch.tensor(scaled_input, dtype=torch.float32)

            # Pass the input data through the model to obtain predictions
            with torch.no_grad():
                predictions = model(input_data.to('cuda'))
                
            # Process the predictions
            predictions = predictions.tolist()
        
        set_bri = predictions[0]
        set_ct = predictions[1]
        
        ## Set Hue lights
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
    'target_cct': f'{target_cct:.2f}',
    'target_lx': f'{target_lx:.2f}',
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
    'resultant_spectrum': outputs_process[2],
    'set_bri': f'{set_bri:.2f}',
    'set_ct': f'{set_ct:.2f}',
    'lights_required': f'{lights_required}'
}
print(json.dumps(output_data))  # Convert the dictionary to JSON and print it
sys.stdout.flush()