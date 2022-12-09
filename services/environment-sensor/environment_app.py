#!/usr/bin/python
# -*- coding:utf-8 -*-
import glob
import json
import os
import socket
import time
import ICM20948 #Gyroscope/Acceleration/Magnetometer
import BME280   #Atmospheric Pressure/Temperature and humidity
import LTR390   #UV
import TSL2591  #LIGHT
import SGP40
from PIL import Image,ImageDraw,ImageFont
from sensirion_gas_index_algorithm.voc_algorithm import VocAlgorithm
import math


bme280 = BME280.BME280()
bme280.get_calib_param()
light = TSL2591.TSL2591()
uv = LTR390.LTR390()
sgp = SGP40.SGP40()
icm20948 = ICM20948.ICM20948()
voc_algorithm = VocAlgorithm()

MINUTES_BETWEEN_WAKES = 0.1
MINUTES_BETWEEN_WRITES = 15
CYCLES_BEFORE_STATUS_CHECK = 1/MINUTES_BETWEEN_WAKES
# if waking up less than once a minute, just set the status check to the same amount of time as the wake cycle
if CYCLES_BEFORE_STATUS_CHECK < 1:
    CYCLES_BEFORE_STATUS_CHECK = MINUTES_BETWEEN_WAKES 

hostname = os.getenv("HOSTNAME", socket.gethostname())
base_dir='/flash/telemetry'
sensor_dir = os.path.join(base_dir, 'sensors')

print("TSL2591 Light I2C address:0X29")
print("LTR390 UV I2C address:0X53")
print("SGP40 VOC I2C address:0X59")
print("icm20948 9-DOF I2C address:0X68")
print("bme280 T&H I2C address:0X76")

def init_sensor_data():
    return {"temperature_c": [],
            "pressure": [],
            "humidity": [],
            "acceleration_x": [],
            "acceleration_y": [],
            "acceleration_z": [],
            "gyroscope_x": [],
            "gyroscope_y": [],
            "gyroscope_z": [],
            "compass_x": [],
            "compass_y": [],
            "compass_z": [],
            "gas_index": [],
            "ultraviolet": [],
            "light_lux": [],
           }

def rename_dotfiles():
    for dotfile in glob.glob(os.path.join(sensor_dir, '.*')):
        basename = os.path.basename(dotfile)
        non_dotfile = os.path.join(sensor_dir, basename[1:])
        os.rename(dotfile, non_dotfile)

def write_sensor_data(sensor_data, timestamp):
    tmp_filename = f'{sensor_dir}/.{hostname}-{timestamp}-environment_sensor_hat.json'  # pytype: disable=name-error
    with open(tmp_filename, 'a') as f:
        for key in sensor_data.keys():
            record = {"target":key, "datapoints": sensor_data[key]}
            f.write(f'{json.dumps(record)}\n')  # pytype: disable=name-error
    rename_dotfiles()  # pytype: disable=name-error

sensor_data = init_sensor_data()

cycles = 1
write_cycles = 1
try:
    while True:
        timestamp = int(time.time()*1000)
        bme = []
        bme = bme280.readData()
        pressure = round(bme[0], 1) 
        temp = round(bme[1], 1) 
        hum = round(bme[2], 1)
        
        lux = round(light.Lux(), 1)
        
        UVS = uv.UVS()
        
        gas = voc_algorithm.process(sgp.raw())
        
        icm = []
        icm = icm20948.getdata()
        roll = round(icm[0], 2)
        pitch = round(icm[1], 2)
        yaw = round(icm[2], 2)
        accel_x = round(icm[3], 2)
        accel_y = round(icm[4], 2)
        accel_z = round(icm[5], 2)
        gyro_x = round(icm[6], 2)
        gyro_y = round(icm[7], 2)
        gyro_z = round(icm[8], 2)
        compass_x = round(icm[9], 2)
        compass_y = round(icm[10], 2)
        compass_z = round(icm[11], 2)

        sensor_data["temperature_c"].append([temp, timestamp])
        sensor_data["pressure"].append([pressure, timestamp])
        sensor_data["humidity"].append([hum, timestamp])
        sensor_data["acceleration_x"].append([accel_x, timestamp])
        sensor_data["acceleration_y"].append([accel_y, timestamp])
        sensor_data["acceleration_z"].append([accel_z, timestamp])
        sensor_data["gyroscope_x"].append([gyro_x, timestamp])
        sensor_data["gyroscope_y"].append([gyro_y, timestamp])
        sensor_data["gyroscope_z"].append([gyro_z, timestamp])
        sensor_data["compass_x"].append([compass_x, timestamp])
        sensor_data["compass_y"].append([compass_y, timestamp])
        sensor_data["compass_z"].append([compass_z, timestamp])
        sensor_data["gas_index"].append([gas, timestamp])
        sensor_data["ultraviolet"].append([UVS, timestamp])
        sensor_data["light_lux"].append([lux, timestamp])

        if cycles == CYCLES_BEFORE_STATUS_CHECK or MINUTES_BETWEEN_WAKES > 1:
            cycles = 1
            write_cycles += 1

        # Write out data
        if write_cycles == MINUTES_BETWEEN_WRITES:
            write_timestamp = int(time.time())
            write_sensor_data(sensor_data, write_timestamp)
            sensor_data = init_sensor_data()
            write_cycles = 1

        time.sleep(60*MINUTES_BETWEEN_WAKES)
        cycles += 1
except KeyboardInterrupt:
    exit()    
