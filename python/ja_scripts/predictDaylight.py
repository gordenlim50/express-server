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

from relatedFunctions import linear_interpolation, alpha_opic_cal, spectrum_inside
from relatedFunctions import window_dist, xyz, xyToCCT, getZonesSPD, cal_all_zones

import torch
import torch.nn as nn
import torch.nn.functional as F

from torchmetrics import Accuracy, MeanSquaredError

from pytorch_lightning.callbacks import EarlyStopping
from pytorch_lightning import LightningModule, Trainer, seed_everything
from pytorch_lightning.callbacks.progress import TQDMProgressBar
from pytorch_lightning.loggers import CSVLogger
from pytorch_lightning.callbacks import Callback, ModelCheckpoint


#--------------------------Code file to Calculate real time sky conditions from weather API---------------------------


class RoomRadiancePredictor(LightningModule):
    def __init__(self, input_dim=10, hidden_dim=128, output_dim=1, learning_rate=1e-4):
        super().__init__()
        
        self.learning_rate = learning_rate
        self.criterion = nn.MSELoss()
        
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, hidden_dim)
        #self.fc4 = nn.Linear(hidden_dim, hidden_dim)
        
        self.fc4 = nn.Linear(hidden_dim, output_dim)
        
        self.train_mse = MeanSquaredError()
        self.val_mse = MeanSquaredError()
        self.test_mse = MeanSquaredError()
        
    def forward(self, x):
        x = x.to(self.fc1.weight.dtype)

        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        #x = F.relu(self.fc4(x))
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
        optimizer = torch.optim.Adam(self.parameters(), lr=self.learning_rate)
        return optimizer
    
    ####################
    # DATA RELATED HOOKS
    ####################

# Getting inputs
curtain_perc = int(sys.argv[1])

# Processing inputs
curtain = curtain_perc / 100

# defining URL parameters
BASE_URL = "http://api.openweathermap.org/data/2.5/weather?"
API_KEY = open('python/ja_scripts/api_key.txt','r').read()
CITY = "Subang Jaya"

# URL
url = BASE_URL + "appid=" + API_KEY + "&q=" + CITY

# Get weather_data response from Weather API
weather_data = requests.get(url).json()

# Getting weather information from the response
latitude = weather_data['coord']['lat']
longitude = weather_data['coord']['lon']
temp_kelvin = weather_data['main']['temp']
temp_celsius = temp_kelvin - 273.15
feels_like_kelvin = weather_data['main']['feels_like']
feels_like_celsius = feels_like_kelvin - 273.15
wind_speed = weather_data['wind']['speed']
humidity = weather_data['main']['humidity']
description = weather_data['weather'][0]['description']
#rainfall = weather_data['rain']['1h']
sunrise_time = dt.datetime.utcfromtimestamp(weather_data['sys']['sunrise'] + weather_data['timezone'])
sunset_time = dt.datetime.utcfromtimestamp(weather_data['sys']['sunset'] + weather_data['timezone'])
retrieve_time = dt.datetime.utcfromtimestamp(weather_data['dt'] + weather_data['timezone'])
cloudiness = weather_data['clouds']['all'] # in percentage
pressure = weather_data['main']['pressure']


# Get the current datetime in the timezone of the weather data
tz_loc = 'Asia/Kuala_Lumpur'
tz = pytz.timezone(tz_loc)
current_time = dt.datetime.now(tz)
time_index = pd.DatetimeIndex([current_time, ])
doy = dt.datetime.now().timetuple().tm_yday

# Create a Location object with the latitude and longitude of the weather data
locationInfo = pvlib.location.Location(name=CITY, latitude=latitude, longitude=longitude, tz=tz_loc)

# Get the solar position for the current time at the location of the weather data
solar_position = pvlib.solarposition.get_solarposition(time=current_time, latitude=latitude, 
                                                       longitude=longitude,temperature=temp_celsius)

# getting solar position metrics
apparent_zenith = solar_position['apparent_zenith']
azimuth = solar_position['azimuth'].values[0]
altitude = solar_position['apparent_elevation'].values[0]
solar_zenith = solar_position['zenith'].values[0]

# Calculate relative air mass and the extra radiation
airmass = pvlib.atmosphere.get_relative_airmass(solar_position['apparent_zenith']).values[0]
dni_extra = pvlib.irradiance.get_extra_radiation(current_time)

# linke turbidity here determines number of clean dry atmospheres that would be necessary to produce 
# the attenuation of the extraterrestrial radiation that is produced by the real atmosphere
linke_turbidity = pvlib.clearsky.lookup_linke_turbidity(time=time_index, latitude=latitude, longitude=longitude).values[0]

# Calculate clear sky parameters using Ineichen/Perez clear sky model
clear_sky = locationInfo.get_clearsky(times=time_index, model='ineichen', solar_position=solar_position, dni_extra=dni_extra)

ghi = clear_sky['ghi'].values[0]
dni = clear_sky['dni'].values[0]
dhi = clear_sky['dhi'].values[0]

if dni != 0 and curtain != 0:
    # parameters to estimate the solar spectral irradiance using Bird Simple Spectral Model
    albedo = 0.15 # surface albedo in Monash
    surface_pressure = pressure*100 # in Pa
    precipitable_water = pvlib.atmosphere.gueymard94_pw(temp_air=temp_celsius, relative_humidity=humidity)
    surface_tilt = 90 ### where the surface is facing (in degrees)
    ozone = 0.25
    tau500 = 0.1
    aoi = pvlib.irradiance.aoi(surface_tilt=surface_tilt, surface_azimuth= 90, solar_zenith=solar_zenith, solar_azimuth=azimuth)

    # Predict daylight spectrum
    spectra = pvlib.spectrum.spectrl2(
        apparent_zenith=altitude,
        aoi=aoi,
        surface_tilt=surface_tilt,
        ground_albedo=albedo,
        surface_pressure=surface_pressure,
        relative_airmass=airmass,
        precipitable_water=precipitable_water,
        ozone=ozone,
        aerosol_turbidity_500nm=tau500,
        dayofyear=doy
    )

    # Visible Spectrum range => [11:48] (360 to 800 nm)
    # Solar Spectrum example => [0:-15]
    wavelengths = spectra['wavelength'][11:48]
    dni_spectrum = spectra['dni'][11:48]
    dhi_spectrum = spectra['dhi'][11:48]
    #poa_spectrum = spectra['poa_sky_diffuse'][11:48]
    global_poa = spectra['poa_global'][11:48]
    ghi_spectrum = dhi_spectrum + dni_spectrum * abs(np.cos(solar_zenith))

    plt_spectrum = global_poa
    plt_spectrum = [float(val[0]) for val in plt_spectrum]

    # Perform linear interpolation---------------------------------------------
    resolution = 5
    desired_wav = np.arange(380,781,resolution)
    estimated_spd = []
    for lamda in desired_wav:
        estimated_spd.append(linear_interpolation(wavelengths, plt_spectrum, lamda))

    plt_spectrum = estimated_spd
    wavelengths = desired_wav
    norm_spec = plt_spectrum / max(plt_spectrum)
    # --------------------------------------------------------------------------

    #-----------------------------------Indoor Daylight Illuminance Model Prediction----------------------------------
    # Load the trained model
    model = RoomRadiancePredictor.load_from_checkpoint('python/ja_scripts/model_2h_128_48.ckpt')

    # Set the model to evaluation mode
    model = model.to('cuda')
    model.eval()

    # Predict indoor daylight illuminances for different zones
    zones_illum = []
    for i in range(24):
        # Prepare your input data for prediction
        position = i+1
        dwr, dwb = window_dist(position)
        model_input = [retrieve_time.hour, retrieve_time.minute, altitude, azimuth, dni, dhi, ghi, dwr, dwb, curtain]
        new_data = model_input  # Load or create new data for prediction
        input_data = torch.tensor(new_data, dtype=torch.float32)

        # Pass the input data through the model to obtain predictions
        with torch.no_grad():
            predictions = model(input_data.to('cuda'))

        # Process the predictions
        predictions = predictions.tolist()
        
        # Illuminance values for every zones
        zones_illum.append(predictions[0])

    #----------------------------------------------------------------------------------------------------------
    avg_illum = statistics.mean(zones_illum)
    # Spectrum inside the room (spectrum after transmitting through windows)
    spd_room = spectrum_inside(plt_spectrum)
    #spd_room = getActualSPD(spd_room, avg_illum)
    zones_spec = getZonesSPD(spd_room, zones_illum)
    
    # calculate lighting metrics for all zones
    plux_all, medi_all, cct_all, cri_all = cal_all_zones(zones_spec)  
else:
    wavelengths = np.arange(380, 781, 5)
    zones_illum = [0] * 24
    plt_spectrum = [0] * 81
    norm_spec = [0] * 81
    zones_spec = [plt_spectrum] * 24
    plux_all = [0] * 24
    medi_all = [0] * 24
    cct_all = [-1] *24
    cri_all = [-1] *24


# # zones => 0 to 23 (zone 1 to zone 24)
# zone = 14
# plux_pred, medi_pred = alpha_opic_cal(zones_spec[zone])
# x,y,z = xyz(zones_spec[zone], 2)
# cct_pred = xyToCCT(x,y)
# print(f"Predicted for zone {zone}: ")
# print(f"CCT = {cct_pred}K")
# print(f"Plux = {plux_pred:.2f}lx")
# print(f"MEDI = {medi_pred:.2f}lx\n")

# # predict spectrum of each position in the room
# plt.plot(wavelengths, zones_spec[zone], label=f"Predicted Spectrum at zone {zone}")
# plt.xlabel("Wavelength (nm)")
# plt.ylabel("Spectral Irradiance (W/m^2/nm)")
# plt.title(f"Predicted Indoor Daylight Spectrum at {retrieve_time}")
# plt.legend()
# plt.show()

# # predict spectrum of outside the room
# plt.plot(wavelengths, norm_spec, label=f"Predicted Daylight Spectrum using pvlib")
# #plt.plot(wavelengths, daylight, label=f"Spectrum measured using CL500")
# plt.xlabel("Wavelength (nm)")
# plt.ylabel("Normalised Spectrum")
# plt.title(f"Predicted Daylight Spectrum at {retrieve_time}")
# plt.legend()
# plt.show()

# print(f"\n========== Weather Information in {CITY} ==========")
# print(f"Temperature: {temp_celsius:.2f}°C")
# print(f"Temperature feels like: {feels_like_celsius:.2f}°C")
# print(f"Humidity: {humidity:.2f} %")
# print(f"Wind Speed: {wind_speed:.2f} m/s")
# print(f"Cloud Cover: {cloudiness:.2f} %")
# print(f"Sun rises at {sunrise_time} local time")
# print(f"Sun sets at {sunset_time} local time")
# print(f"Description: {description}")
# print(f"Weather retrieving time: {retrieve_time}\n")

# # Print sky parameters
# print(f"=========================== Sky Parameters ===========================")
# print(f"Cloudiness: {cloudiness} %")
# print(f"Air mass: {airmass:.2f}")
# print(f"Direct Normal Irradiance (DNI): {dni:.2f} W/m^2")
# print(f"Diffuse Horizontal Irradiance (DHI): {dhi:.2f} W/m^2")
# print(f"Global Horizontal Irradiance (GHI): {ghi:.2f} W/m^2")
# print(f"Sun Altitude: {altitude:.2f}°")
# print(f"Sun Azimuth: {azimuth:.2f}°\n\n")

# print(f"DATA CALCULATION TIME: {retrieve_time}\n")




# # predict spectrum of outside the room
# plt.plot(wavelengths, plt_spectrum, label=f"Predicted Daylight Spectrum using pvlib", color="gray")
# plt.xlabel("Wavelength (nm)")
# plt.ylabel("Spectral Irradiance")
# plt.title(f"Predicted Daylight Spectrum at {retrieve_time}")

# # plot spectrum with colors
# plot_data = plt_spectrum
# colors = np.array(np.vectorize(wavelength_to_rgb)(wavelengths))
# for i in range(len(wavelengths) - 1):
#     plt.fill_between([wavelengths[i], wavelengths[i+1]], [plot_data[i], plot_data[i+1]], color=colors[:, i])
# plt.show()
wavelengths = wavelengths.tolist()

norm_spec = np.array(norm_spec)
norm_spec = norm_spec.tolist()

# Handle output result
output_data = {
    'city': f'{CITY}',
    'temperature': f'{temp_celsius:.2f}',
    'humidity': f'{humidity:.2f}',
    'wind_speed': f'{wind_speed:.2f}',
    'cloud_cover': f'{cloudiness}',
    'sunrise_time': f'{sunrise_time}',
    'sunset_time': f'{sunset_time}',
    'description': f'{description}',
    'retrieve_time': f'{retrieve_time}',
    'air_mass': f'{airmass}',
    'sun_altitude': f'{altitude}',
    'sun_azimuth': f'{azimuth}',
    'dni': f'{dni}',
    'dhi': f'{dhi}',
    'ghi': f'{ghi}',
    'wavelengths': wavelengths,
    'normalised_daylight': norm_spec,
    'zones_spectrum': zones_spec,
    'zones_illuminance': zones_illum,
    'plux_all': plux_all,
    'cct_all': cct_all,
    'medi_all': medi_all,
    'cri_all': cri_all
}
print(json.dumps(output_data))  # Convert the dictionary to JSON and print it
sys.stdout.flush()
