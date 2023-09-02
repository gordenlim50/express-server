import datetime as dt
import requests
import pandas as pd
import pvlib # library for photovoltaic system
import pytz
import numpy as np
import matplotlib.pyplot as plt
import csv
import statistics
import json
import sys

from relatedFunctions import linear_interpolation, alpha_opic_cal, D_illuminant
from relatedFunctions import window_dist, xyz, xyToCCT, getZonesSPD, getActualSPD

# Getting inputs (inputs = [(dk what is this), [indoor daylight spectrum (1 zone)], targetvalues])
pred_spd = sys.argv[1]
target_cct = float(sys.argv[2])
target_plux = float(sys.argv[3])
target_medi = float(sys.argv[4])



#target_plux = 300
#target_cct = 5000
target_spec = D_illuminant(target_cct)
target_spec = getActualSPD(target_spec, target_plux)
spec_temp = []
for i in range(len(target_spec)):
    spec_temp.append(target_spec[i]-pred_spd[i])

required_spec = spec_temp

# Calculate metrics of the required spectrum
plux_req, medi_req = alpha_opic_cal(required_spec)
x_req,y_req,z_req = xyz(required_spec, 2)
cct_req = xyToCCT(x_req,y_req)
mder_req = medi_req / plux_req


print(f"Metrics required ")
print(f"CCT = {cct_req}K")
print(f"Plux = {plux_req:.2f}lx")
print(f"MEDI = {medi_req:.2f}lx")
print(f"MDER = {mder_req:.2f}\n")