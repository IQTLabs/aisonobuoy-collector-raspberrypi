# using pyais 1.5.0
from pyais import decode_raw

import json
import os
import serial
import socket
import time

SERIAL_PORT = "/dev/serial0"
running = True

print("AIS application started!")
aisc = serial.Serial(SERIAL_PORT, baudrate=38400, timeout=1)


def getAIS(aisc, results):
    data = aisc.readline()
    if data:
        try:
            msg = decode_raw(data)
            timestamp = int(time.time()*1000)
            for key in msg.keys():
                if key in ['status', 'maneuver', 'epfd', 'shiptype', 'aid_type', 'station_type', 'ship_type', 'txrx', 'interval']:
                    msg[key] = msg[key].name
            msg['timestamp'] = timestamp
            print(f'{msg}')
            results.append(msg)
        except Exception as e:
            print(f'Bad formatted data: {data}')
    return results

start_time = int(time.time()*1000)
records = []
while running:
    hostname = socket.gethostname()
    f_dir = f'/flash/telemetry/ais'
    os.makedirs(f_dir, exist_ok=True)
    try:
        # check if 15 minutes have elapsed
        if int(time.time()*1000) >= (start_time + 900000):
            start_time = int(time.time()*1000)
        if len(records) > 0:
            with open(f'{f_dir}/{hostname}-{start_time}-ais.json', 'a', encoding="utf-8") as f:
                for record in records:
                    try:
                        f.write(f'{json.dumps(record)}\n')
                    except Exception as e:
                        f.write('{"error":"'+str(record)+'"}\n')
            records = []
        records = getAIS(aisc, records)
        sleep_time = 1
        time.sleep(sleep_time)
    except KeyboardInterrupt:
        running = False
        aisc.close()
        print("AIS application stopped!")
    except Exception as e:
        print(f"AIS application error: {e}")
