import glob
import json
import os
import socket
import subprocess
import time

from sense_hat import SenseHat  # pytype: disable=import-error


# Raw colors
red = (255, 0, 0)
yellow = (255, 255, 0)
blue = (0, 0, 255)
white = (255, 255, 255)
off = (0, 0, 0)


class Telemetry:

    def __init__(self, base_dir='/flash/telemetry'):
        # plus 0.5 second for status per wake and plus time to run loop
        self.MINUTES_BETWEEN_WAKES = 0.1  # roughly every 5 seconds (not 6 because of the above considerations)
        self.MINUTES_BETWEEN_WRITES = 15
        self.CYCLES_BEFORE_STATUS_CHECK = 1/self.MINUTES_BETWEEN_WAKES
        # if waking up less than once a minute, just set the status check to the same amount of time as the wake cycle
        if self.CYCLES_BEFORE_STATUS_CHECK < 1:
            self.CYCLES_BEFORE_STATUS_CHECK = self.MINUTES_BETWEEN_WAKES

        self.hostname = os.getenv("HOSTNAME", socket.gethostname())
        self.sensor_dir = os.path.join(base_dir, 'sensors')
        self.sense = None
        self.sensor_data = None

    def init_sense(self):
        self.sense = SenseHat()
        self.sense.clear()
        self.sense.low_light = True

    def get_temperature(self):
        # rounded to one decimal place
        return round(self.sense.get_temperature(), 1)

    def get_humidity(self):
        # rounded to one decimal place
        return round(self.sense.get_humidity(), 1)

    def get_pressure(self):
        # rounded to one decimal place
        return round(self.sense.get_pressure(), 1)

    def get_acceleration(self):
        acceleration = self.sense.get_accelerometer_raw()
        # rounded to two decimal places
        x = round(acceleration['x'], 2)
        y = round(acceleration['y'], 2)
        z = round(acceleration['z'], 2)
        return x, y, z

    def get_gyro(self):
        gyro = self.sense.get_gyroscope_raw()
        # rounded to two decimal places
        x = round(gyro['x'], 2)
        y = round(gyro['y'], 2)
        z = round(gyro['z'], 2)
        return x, y, z

    def get_compass(self):
        compass = self.sense.get_compass_raw()
        # rounded to two decimal places
        x = round(compass['x'], 2)
        y = round(compass['y'], 2)
        z = round(compass['z'], 2)
        return x, y, z

    def display(self, x, y, color):
        self.sense.set_pixel(x, y, color)

    def read_sensors(self, timestamp):
        t = self.get_temperature()
        self.sensor_data["temperature_c"].append([t, timestamp])
        if t < 5 or t > 70:
            self.display(6, 3, red)
        elif t < 10 or t > 65:
            self.display(6, 3, yellow)
        else:
            self.display(6, 3, blue)
        p = self.get_pressure()
        self.sensor_data["pressure"].append([p, timestamp])
        self.display(5, 3, blue)
        h = self.get_humidity()
        self.sensor_data["humidity"].append([h, timestamp])
        self.display(4, 3, blue)
        ax, ay, az = self.get_acceleration()
        self.sensor_data["acceleration_x"].append([ax, timestamp])
        self.sensor_data["acceleration_y"].append([ay, timestamp])
        self.sensor_data["acceleration_z"].append([az, timestamp])
        self.display(6, 4, blue)
        gx, gy, gz = self.get_gyro()
        self.sensor_data["gyroscope_x"].append([gx, timestamp])
        self.sensor_data["gyroscope_y"].append([gy, timestamp])
        self.sensor_data["gyroscope_z"].append([gz, timestamp])
        self.display(5, 4, blue)
        cx, cy, cz = self.get_compass()
        self.sensor_data["compass_x"].append([cx, timestamp])
        self.sensor_data["compass_y"].append([cy, timestamp])
        self.sensor_data["compass_z"].append([cz, timestamp])
        self.display(4, 4, blue)

    def init_sensor_data(self):
        self.sensor_data = {"temperature_c": [],
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
                           }

    def rename_dotfiles(self):
        for dotfile in glob.glob(os.path.join(self.sensor_dir, '.*')):
            basename = os.path.basename(dotfile)
            non_dotfile = os.path.join(self.sensor_dir, basename[1:])
            os.rename(dotfile, non_dotfile)

    def write_sensor_data(self, timestamp):
        tmp_filename = f'{self.sensor_dir}/.{self.hostname}-{timestamp}-sensehat.json'
        with open(tmp_filename, 'a') as f:
            for key in self.sensor_data.keys():
                record = {"target":key, "datapoints": self.sensor_data[key]}
                f.write(f'{json.dumps(record)}\n')
        self.rename_dotfiles()

    def main(self, run_forever):
        os.makedirs(self.sensor_dir, exist_ok=True)
        self.init_sensor_data()

        # Throwaway readings to calibrate
        for i in range(5):
            # Light up top left to indicate running calibration
            self.display(7, 7, white)
            t = self.get_temperature()
            p = self.get_pressure()
            h = self.get_humidity()
            ax, ay, az = self.get_acceleration()
            gx, gy, gz = self.get_gyro()
            cx, cy, cz = self.get_compass()

        # Turn off top left to indicate calibration is done
        self.display(7, 7, off)

        # Cycle through getting readings forever
        cycles = 1
        write_cycles = 1
        user_shutdown = False
        running = True
        while running:
            running = run_forever

            # TODO: write out data if exception with a try/except
            timestamp = int(time.time()*1000)

            # Light up top left pixel for cycle
            self.display(7, 7, blue)

            if cycles == self.CYCLES_BEFORE_STATUS_CHECK or self.MINUTES_BETWEEN_WAKES > 1:
                cycles = 1
                write_cycles += 1

            # Take readings from sensors
            self.read_sensors(timestamp)

            # Write out data
            if write_cycles == self.MINUTES_BETWEEN_WRITES:
                write_timestamp = int(time.time())
                self.write_sensor_data(write_timestamp)
                self.init_sensor_data()
                write_cycles = 1

            # Keep lights for 0.5 second
            light_time = 0.5
            time.sleep(light_time)

            # Turn off all pixels
            self.sense.set_pixels([off]*64)

            # Sleep between cycles
            time.sleep(60*self.MINUTES_BETWEEN_WAKES)

            cycles += 1


if __name__ == '__main__':
    t = Telemetry()
    t.init_sense()
    t.main(True)
