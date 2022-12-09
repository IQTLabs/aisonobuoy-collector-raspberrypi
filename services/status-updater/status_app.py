import copy
import glob
import json
import os
import socket
import subprocess
import time
from collections import defaultdict

import docker

from hooks import insert_message_data
from hooks import send_hook


class Telemetry:

    SHUTDOWN_PATH = '/var/run/shutdown.signal'

    def __init__(self, base_dir='/flash/telemetry'):
        # plus 0.5 second for status per wake and plus time to run loop
        self.MINUTES_BETWEEN_WAKES = 0.1  # roughly every 5 seconds (not 6 because of the above considerations)
        self.MINUTES_BETWEEN_WRITES = 5
        self.CYCLES_BEFORE_STATUS_CHECK = 1/self.MINUTES_BETWEEN_WAKES
        # if waking up less than once a minute, just set the status check to the same amount of time as the wake cycle
        if self.CYCLES_BEFORE_STATUS_CHECK < 1:
            self.CYCLES_BEFORE_STATUS_CHECK = self.MINUTES_BETWEEN_WAKES

        self.hostname = os.getenv("HOSTNAME", socket.gethostname())
        self.location = os.getenv("LOCATION", "unknown")
        self.version = os.getenv("VERSION", "")
        self.sensor_dir = os.path.join(base_dir, 'sensors')
        self.status_dir = os.path.join(base_dir, 'status')
        self.ais_dir = os.path.join(base_dir, 'ais')
        self.gps_dir = os.path.join(base_dir, 'gps')
        self.hydrophone_dir = os.path.join(base_dir, 'hydrophone')
        self.power_dir = os.path.join(base_dir, 'power')
        self.s3_dir = '/flash/s3'
        self.ais_file = os.path.join(self.ais_dir, 'false')
        self.ais_records = 0
        self.gps_file = os.path.join(self.gps_dir, 'false')
        self.hydrophone_file = os.path.join(self.hydrophone_dir, 'false')
        self.hydrophone_size = 0
        self.power_file = os.path.join(self.power_dir, 'false')
        self.sensor_file = os.path.join(self.sensor_dir, 'false')
        self.alerts = {}
        self.docker = docker.from_env()
        self.init_sensor_data()

    def check_version(self, timestamp):
        healthy = True
        unhealthy_containers = []
        containers = self.docker.containers.list()
        for container in containers:
            try:
                if container.name.startswith('services_'):
                    if container.status != 'running':
                        healthy = False
                        unhealthy_containers.append(container.name.split('_')[1])
                    if container.name.split('_')[1] in self.sensor_data:
                        self.sensor_data[container.name.split('_')[1]].append(
                            [self.get_container_version(container), timestamp])
                    else:
                        self.sensor_data[container.name.split('_')[1]] = [[self.get_container_version(container), timestamp]]
            except Exception as e:
                if container.name.split('_')[1] in self.sensor_data:
                    self.sensor_data[container.name.split('_')[1]].append([str(e), timestamp])
                else:
                    self.sensor_data[container.name.split('_')[1]] = [[str(e), timestamp]]
                healthy = False
        if 'unhealthy_containers' in self.sensor_data:
            self.sensor_data['unhealthy_containers'].append([" ".join(unhealthy_containers), timestamp])
        else:
            self.sensor_data['unhealthy_containers'] = [[" ".join(unhealthy_containers), timestamp]]
        return healthy

    @staticmethod
    def check_internet():
        try:
            output = subprocess.check_output("/internet_check.sh")
        except Exception as e:
            print(f'Failed to check internet because: {e}')
            output = b'Failed'

        if b'Online' in output:
            return True
        return False

    def get_container_version(self, container):
        env_vars = container.attrs['Config']['Env']
        for env_var in env_vars:
            if env_var.startswith("VERSION="):
                return env_var.split("=")[-1]
        return container.image.tags[0].split(':')[1]

    @staticmethod
    def reorder_dots(files):
        last_dot = -1
        for i, f in enumerate(files):
            if f.startswith('.'):
                last_dot = i
        last_dot += 1
        files = files[last_dot:] + files[0:last_dot]
        return files

    def check_ais(self):
        # check for new files, in the newest file, check if the number of lines has increased
        try:
            files = sorted([f for f in os.listdir(self.ais_dir) if os.path.isfile(os.path.join(self.ais_dir, f))])
            # check for dotfiles
            files = self.reorder_dots(files)
        except FileNotFoundError:
            files = None

        if not files:
            self.ais_file = os.path.join(self.ais_dir, 'false')
            self.ais_records = 0
            return False
        elif os.path.join(self.ais_dir, files[-1]) != self.ais_file:
            self.ais_file = os.path.join(self.ais_dir, files[-1])
            self.ais_records = sum(1 for line in open(self.ais_file))
            return True
        # file already exists, check if there's new records
        num_lines = sum(1 for line in open(self.ais_file))
        if num_lines > self.ais_records:
            self.ais_records = num_lines
            return True
        return False

    def check_gps(self, timestamp):
        try:
            files = sorted([f for f in os.listdir(self.gps_dir) if os.path.isfile(os.path.join(self.gps_dir, f))])
            # check for dotfiles
            files = self.reorder_dots(files)
        except FileNotFoundError:
            files = None

        if not files:
            self.gps_file = os.path.join(self.gps_dir, 'false')
            return
        elif os.path.join(self.gps_dir, files[-1]) != self.gps_file:
            self.gps_file = os.path.join(self.gps_dir, files[-1])
        with open(self.gps_file, 'r') as f:
            for line in f:
                if 'status:' in line:
                    if 'gps_status' in self.sensor_data:
                        self.sensor_data['gps_status'].append([line.split('status:')[-1].strip(), timestamp])
                    else:
                        self.sensor_data['gps_status'] = [[line.split('status:')[-1].strip(), timestamp]]
                elif 'latitude:' in line:
                    if 'latitude' in self.sensor_data:
                        self.sensor_data['latitude'].append([line.split('latitude:')[-1].split('degrees')[0].strip(), timestamp])
                    else:
                        self.sensor_data['latitude'] = [[line.split('latitude:')[-1].split('degrees')[0].strip(), timestamp]]
                elif 'longitude:' in line:
                    if 'longitude' in self.sensor_data:
                        self.sensor_data['longitude'].append([line.split('longitude:')[-1].split('degrees')[0].strip(), timestamp])
                    else:
                        self.sensor_data['longitude'] = [[line.split('longitude:')[-1].split('degrees')[0].strip(), timestamp]]
                elif 'circular horizontal position uncertainty:' in line:
                    if 'position_uncertainty_meters' in self.sensor_data:
                        self.sensor_data['position_uncertainty_meters'].append([line.split('circular horizontal position uncertainty:')[-1].split('meters')[0].strip(), timestamp])
                    else:
                        self.sensor_data['position_uncertainty_meters'] = [[line.split('circular horizontal position uncertainty:')[-1].split('meters')[0].strip(), timestamp]]
                elif 'technology:' in line:
                    if 'gps_technology' in self.sensor_data:
                        self.sensor_data['gps_technology'].append([line.split('technology:')[-1].strip(), timestamp])
                    else:
                        self.sensor_data['gps_technology'] = [[line.split('technology:')[-1].strip(), timestamp]]
                elif 'Satellites used:' in line:
                    if 'gps_sats' in self.sensor_data:
                        self.sensor_data['gps_sats'].append([line.split('Satellites used:')[-1].strip(), timestamp])
                    else:
                        self.sensor_data['gps_sats'] = [[line.split('Satellites used:')[-1].strip(), timestamp]]

    def check_sensor(self):
        try:
            files = sorted([f for f in os.listdir(self.sensor_dir) if os.path.isfile(os.path.join(self.sensor_dir, f))])
            # check for dotfiles
            files = self.reorder_dots(files)
        except FileNotFoundError:
            files = None

        if not files:
            self.sensor_file = os.path.join(self.sensor_dir, 'false')
            return
        elif os.path.join(self.sensor_dir, files[-1]) != self.sensor_file:
            self.sensor_file = os.path.join(self.sensor_dir, files[-1])
        with open(self.sensor_file, 'r') as f:
            for line in f:
                record = json.loads(line.strip())
                if record['target'] in self.sensor_data:
                    self.sensor_data[record['target']].append(record['datapoints'][-1])
                else:
                    self.sensor_data[record['target']] = [record['datapoints'][-1]]

    def check_power(self):
        try:
            files = sorted([f for f in os.listdir(self.power_dir) if os.path.isfile(os.path.join(self.power_dir, f))])
            # check for dotfiles
            files = self.reorder_dots(files)
        except FileNotFoundError:
            files = None

        if not files:
            self.power_file = os.path.join(self.power_dir, 'false')
            return
        elif os.path.join(self.power_dir, files[-1]) != self.power_file:
            self.power_file = os.path.join(self.power_dir, files[-1])
        with open(self.power_file, 'r') as f:
            for line in f:
                record = json.loads(line.strip())
                if record['target'] in self.sensor_data:
                    self.sensor_data[record['target']].append(record['datapoints'][-1])
                else:
                    self.sensor_data[record['target']] = [record['datapoints'][-1]]

    def check_hydrophone(self):
        try:
            files = sorted([f for f in os.listdir(self.hydrophone_dir) if os.path.isfile(os.path.join(self.hydrophone_dir, f))])
            # check for dotfiles
            files = self.reorder_dots(files)
        except FileNotFoundError:
            files = None

        # no files
        if not files:
            self.hydrophone_file = os.path.join(self.hydrophone_dir, 'false')
            self.hydrophone_size = 0
            return False
        # found a new file
        elif os.path.join(self.hydrophone_dir, files[-1]) != self.hydrophone_file:
            self.hydrophone_file = os.path.join(self.hydrophone_dir, files[-1])
            self.hydrophone_size = os.path.getsize(self.hydrophone_file)
            return True
        # file already exists, check the size
        size = os.path.getsize(self.hydrophone_file)
        if size > self.hydrophone_size:
            self.hydrophone_size = size
            return True
        return False

    def check_s3(self):
        try:
            files = sorted([f for f in os.listdir(self.s3_dir) if os.path.isfile(os.path.join(self.s3_dir, f))])
        except FileNotFoundError:
            files = None

        if not files:
            return False, 0
        else:
            return True, len(files)

    def init_sensor_data(self):
        self.sensor_data = defaultdict(list)
        self.sensor_data.update({
            "location": [self.location],
            "system_load": [],
            "memory_used_mb": [],
            "internet": [],
            "disk_free_gb": [],
            "uptime_seconds": []})

    def rename_dotfiles(self):
        for dotfile in glob.glob(os.path.join(self.status_dir, '.*')):
            basename = os.path.basename(dotfile)
            non_dotfile = os.path.join(self.status_dir, basename[1:])
            os.rename(dotfile, non_dotfile)

    def write_sensor_data(self, timestamp):
        status = self.status_hook()
        tmp_filename = f'{self.status_dir}/.status-{self.hostname}-{timestamp}.json'
        payload = copy.deepcopy(self.sensor_data)
        for key in payload.keys():
            payload[key] = payload[key][-1]
        payload['alerts'] = self.alerts
        with open(tmp_filename, 'w') as f:
            json.dump(payload, f)
        self.rename_dotfiles()
        print(f'Status update response: {status}')

    def shutdown_hook(self, subtitle):
        data = {}
        data['title'] = os.path.join(self.hostname, self.location)
        data['themeColor'] = "d95f02"
        data['body_title'] = "Shutting system down"
        data['body_subtitle'] = subtitle
        data['text'] = ""
        data['facts'] = self.status_data()
        card = insert_message_data(data)
        status = send_hook(card)
        return status

    def status_hook(self):
        checks = len(self.alerts)
        health = 0
        unhealthy = []
        for alert in self.alerts:
            if self.alerts[alert]:
                unhealthy.append(alert)
            else:
                health += 1

        data = {}
        data['title'] = os.path.join(self.hostname, self.location)
        data['body_title'] = "Status Update"
        data['body_subtitle'] = f'{health} / {checks} checks healthy'
        if health < checks:
            data['themeColor'] = "d95f02"
        data['text'] = f'Checks that alerted: {" ".join(unhealthy)}'
        data['facts'] = self.status_data()
        card = insert_message_data(data)
        status = send_hook(card)
        return status

    def status_data(self):
        facts = []
        for key in self.sensor_data.keys():
            if len(self.sensor_data[key]) > 0:
                facts.append({"name": key, "value": str(self.sensor_data[key][-1][0])})
        return facts

    def run_checks(self, timestamp):
        # internet: check if available
        inet = self.check_internet()
        self.sensor_data["internet"].append([inet, timestamp])
        if inet:
            self.alerts['internet'] = False
        else:
            self.alerts['internet'] = True

        # version and docker container health:
        healthy = self.check_version(timestamp)
        if healthy:
            self.alerts['healthy'] = False
        else:
            self.alerts['healthy'] = True

        # ais: see if new detection since last cycle
        ais = self.check_ais()
        if ais:
            if "ais_record" in self.sensor_data:
                self.sensor_data["ais_record"].append([ais, timestamp])
            else:
                self.sensor_data["ais_record"] = [[ais, timestamp]]

        # recordings: see if new recording file since last session, or if more bytes have been written
        hydrophone = self.check_hydrophone()
        if hydrophone:
            if "audio_record" in self.sensor_data:
                self.sensor_data["audio_record"].append([hydrophone, timestamp])
            else:
                self.sensor_data["audio_record"] = [[hydrophone, timestamp]]

        # files to upload to s3
        s3, s3_files = self.check_s3()
        if s3:
            if "files_to_upload" in self.sensor_data:
                self.sensor_data["files_to_upload"].append([s3_files, timestamp])
            else:
                self.sensor_data["files_to_upload"] = [[s3_files, timestamp]]

        # battery: check current battery level from pijuice hopefully, change color based on level
        self.check_power()
        if 'battery_status' in self.sensor_data:
            if len(self.sensor_data['battery_status']) > 0:
                if self.sensor_data['battery_status'][-1][0] in ['NORMAL', 'CHARGING_FROM_IN']:
                    self.alerts['battery_status'] = False
                else:
                    self.alerts['battery_status'] = True
        if 'battery_charge' in self.sensor_data:
            if len(self.sensor_data['battery_charge']) > 0:
                if int(self.sensor_data['battery_charge'][-1][0]) > 20:
                    self.alerts['battery_charge'] = False
                else:
                    self.alerts['battery_charge'] = True

        # sensor readings: temp, humidity, pressure, lux, uv, gas, 9DOF
        self.check_sensor()
        if 'temperature_c' in self.sensor_data:
            if len(self.sensor_data['temperature_c']) > 0:
                if self.sensor_data['temperature_c'][-1][0] < 10 or self.sensor_data['temperature_c'][-1][0] > 65:
                    self.alerts['temperature_c'] = True
                else:
                    self.alerts['temperature_c'] = False

        # gps readings
        self.check_gps(timestamp)
        if 'gps_status' in self.sensor_data:
            if len(self.sensor_data['gps_status']) > 0:
                if self.sensor_data['gps_status'][-1][0] == 'success':
                    self.alerts['gps_status'] = False
                else:
                    self.alerts['gps_status'] = True
        
        # system health: load
        load = os.getloadavg()
        self.sensor_data["system_load"].append([load[0], timestamp])
        if load[0] > 2:
            self.alerts['system_load'] = True
        elif load[0] > 1:
            self.alerts['system_load'] = False
        else:
            self.alerts['system_load'] = False

        # system health: memory
        total_memory, used_memory, free_memory = map(int, os.popen('free -t -m').readlines()[1].split()[1:4])
        self.sensor_data["memory_used_mb"].append([used_memory, timestamp])
        if used_memory/total_memory > 0.9:
            self.alerts['memory_used_mb'] = True
        elif used_memory/total_memory > 0.7:
            self.alerts['memory_used_mb'] = False
        else:
            self.alerts['memory_used_mb'] = False

        # system health: disk space
        st = os.statvfs('/')
        bytes_avail = (st.f_bavail * st.f_frsize)
        gb_free = round(bytes_avail / 1024 / 1024 / 1024, 1)
        self.sensor_data["disk_free_gb"].append([gb_free, timestamp])
        if gb_free < 2:
            self.alerts['disk_free_gb'] = True
        elif gb_free < 10:
            self.alerts['disk_free_gb'] = False
        else:
            self.alerts['disk_free_gb'] = False

        # system uptime (linux only!)
        self.sensor_data["uptime_seconds"].append([time.clock_gettime(time.CLOCK_BOOTTIME), timestamp])

    def main(self, run_forever):
        os.makedirs(self.status_dir, exist_ok=True)
        self.init_sensor_data()

        # Cycle through getting readings forever
        cycles = 1
        write_cycles = 1
        running = True
        while running:
            running = run_forever

            # TODO: write out data if exception with a try/except
            timestamp = int(time.time()*1000)

            # Check if a shutdown has been signaled
            signal_contents = ""

            if os.path.exists(self.SHUTDOWN_PATH) and os.access(self.SHUTDOWN_PATH, os.R_OK):
                with open('/var/run/shutdown.signal', 'r') as f:
                     signal_contents = f.read()

            if signal_contents.strip() == 'true':
                self.shutdown_hook("Low battery")

            if cycles == self.CYCLES_BEFORE_STATUS_CHECK or self.MINUTES_BETWEEN_WAKES > 1:
                self.run_checks(timestamp)
                cycles = 1
                write_cycles += 1

            # Write out data
            if write_cycles == self.MINUTES_BETWEEN_WRITES:
                write_timestamp = int(time.time())
                self.write_sensor_data(write_timestamp)
                self.init_sensor_data()
                write_cycles = 1

            # Sleep between cycles
            time.sleep(60*self.MINUTES_BETWEEN_WAKES)

            cycles += 1


if __name__ == '__main__':
    t = Telemetry()
    t.main(True)
