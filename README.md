<img src="./media/pibuoy2-hydrophone-solar.png" alt="pibuoy" height="400px" title="pibuoy">

The following are the hardware and software requirements and installation instructions for the Raspberry Pi Zero buoy version.

# Hardware Requirements

- Raspberry Pi Zero 2 W
- HiFiBerry DAC+ADC Pro
- dAISy HAT
- Environment Sensor HAT
- SIM7600G-H 4G HAT (B)
- PiJuice Zero
- pHAT Stack
- 12000mAh PiJuice Battery
- H2A Hydrophone
- Seahorse 56 Micro Case
- [3D Printed Chassis](stl-files)

# Hardware configuration installation

1. Solder Pi Zero 2 W stacking header.

2. Add Mic Bias jumpers to the HiFiBerry HAT.

3. Remove pin 12 from the header attached to the dAISy HAT.

<img src="./media/pibuoy2-hydrophone-solar-exploded.png" alt="pibuoy" height="400px" title="pibuoy">

# Deployments

## PiBuoy

Having deployed the first buoy, PiBuoy v1 Mark I, that was designed from the ground up (several learnings were integrated from the [Maker Buoy](https://www.makerbuoy.com/)) for data collection for this project before replicating the buildout of it proved more difficult than expected. Recently, while trying to remotely replicate the Mark I, there was difficulty in making the [Sixfab 3G-4G/LTE Base HAT](https://sixfab.com/product/raspberry-pi-4g-lte-modem-kit/) (the data connection for the buoy) work with the cell network provider we had chosen despite having seemingly configured everything correctly.

<img src="/docs/img/sixfab_buoy.jpg" height="300" alt="Sixfab HAT on top of a RaspberryPi, additional wiring in the configuration for the buoy"/>

Not having a spare SIM card attached to a network provider to reproduce the setup locally proved difficult at first, until the idea of leveraging the work from [Daedalus]( https://github.com/IQTLabs/Daedalus) came to mind. With Daedalus, one can provision their own SIM card with whatever APN and settings they’d like and connect devices using a software-defined radio (SDR) to create a private 4G LTE/5G network that provides a data connection over the network connection of the machine running Daedalus. Using the [Daedalus tool]( https://github.com/IQTLabs/Daedalus/blob/main/blue/README.md), we were able to demonstrate the settings on the Sixfab and modem were configured correctly which greatly reduced the amount of remote debugging that was needed.

<img src="/docs/img/sixfab_bladerf.jpg" height="300" alt="Sixfab with SIM card on top of a RaspberryPi next to the BladeRF SDR"/>

In this case, the issue ended up being extremely poor signal inside of an office building, that once cleanly started in an environment that had a clear signal the connection worked as expected.

# Initial installation

1. Install Raspberry Pi OS (choose 'Raspberry Pi OS other' and then 'Raspberry Pi OS Lite 32-bit' based on Debian Bullseye) on the SD card for the Raspberry Pi using Raspberry Pi Imager.
- Use `CTRL+SHIFT+x` to use advanced options when flashing the SD card. Set the hostname, enable SSH and add a password or key, configure WiFi and set the correct WiFi country, set the locale settings and Skip the first-run wizard.

2. Install required packages.
```
sudo apt-get update
sudo apt-get install build-essential git python3-pip python3-smbus python3-urwid screen tmux
```

3. Disable unneeded services.
```
sudo systemctl stop avahi-daemon.service
sudo systemctl stop avahi-daemon.socket
sudo systemctl stop apt-daily-upgrade.service
sudo systemctl stop apt-daily-upgrade.timer
sudo systemctl disable avahi-daemon.service
sudo systemctl disable avahi-daemon.socket
sudo systemctl disable apt-daily-upgrade.service
sudo systemctl disable apt-daily-upgrade.timer
```

4. Disable tvservice since the system is headless by adding `/usr/bin/tvservice -o` to `/etc/rc.local` before the `exit 0`.

5. Install this repo.
```
sudo su -
cd /opt
git clone https://github.com/IQTLabs/AISonobuoy.git
```

6. Install Docker.
```
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker pi
```

7. Install docker-compose.
```
sudo pip3 install docker-compose
```

8. Put the config.txt in `/boot/config.txt`.
```
sudo cp /opt/AISonobuoy/PiBuoyV2/config.txt /boot/config.txt
```

9. Setup [dAISy HAT](https://wegmatt.com/files/dAISy%20HAT%20AIS%20Receiver%20Manual.pdf).
```
wget https://github.com/itemir/rpi_boat_utils/raw/master/uart_control/uart_control
chmod +x ./uart_control
sudo ./uart_control gpio
```

10. Schedule jobs in crontab.
```
sudo crontab -e
```
Add the following lines, save, and quit:
```
# every five minutes
*/5 * * * * /opt/AISonobuoy/PiBuoyV2/scripts/system_health.sh
# every thirty minutes
*/30 * * * * systemctl restart pijuice.service
# every minute check if need to shutdown
* * * * * /opt/AISonobuoy/PiBuoyV2/scripts/shutdown.sh
```

11. Add [AWS credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) so you have ~/.aws/credentials and ~/.aws/config that have a role that can write to the S3 bucket.

12. Enable I2C in raspi-config.
```
sudo raspi-config
-> Interface Options -> I2C -> Yes to enable
```

13. Install PiJuice service.
```
git clone https://github.com/PiSupply/PiJuice.git
cd PiJuice/Software/Install
sudo dpkg -i ./pijuice-base_1.8_all.deb
```

14. Restart.
```
sudo reboot
```

15. Change the I2C address of the RTC on the pijuice, from the menu choose `General`, change the I2C address RTC value from 68 to 69 (0x68 conflicts with the 9DOF on the environment sensor hat), Apply settings.
```
pijuice_cli
```

16. Update the firmware on the PiJuice to V1.6 (choose `Firmware` from the menu). Note: this will power cycle the Pi if a battery isn't attached.
```
pijuice_cli
```

17. Update `/opt/AISonobuoy/PiBuoyV2/.env` to suit deployment needs.

18. Start PiBuoy containers.
```
cd /opt/AISonobuoy/PiBuoyV2
docker-compose up -d
```

# Verify components are working
1. Check logs in `/var/log/syslog`, `/var/log/messages`.

2. Check `dmesg` for errors.

3. Check for data in `/flash/telemetry`.

4. Verify containers are running with `docker ps`.
```
$ docker ps
CONTAINER ID   IMAGE                                 COMMAND                  CREATED          STATUS          PORTS      NAMES
b76503cfbada   iqtlabs/aisonobuoy-s3-upload:latest   "/prep_and_send.sh "     36 minutes ago   Up 36 minutes              pibuoyv2_s3-upload_1
492f3adf50a1   iqtlabs/aisonobuoy-sense:latest       "python3 /app.py "       36 minutes ago   Up 36 minutes              pibuoyv2_sense_1
0e5a09f23127   iqtlabs/aisonobuoy-record:latest      "/record.sh "            36 minutes ago   Up 6 minutes               pibuoyv2_record_1
da6bd9f59e0e   iqtlabs/aisonobuoy-ais:latest         "python3 /app.py "       36 minutes ago   Up 36 minutes              pibuoyv2_ais_1
2bc024492d88   containrrr/watchtower:armhf-latest    "/watchtower"            36 minutes ago   Up 36 minutes   8080/tcp   pibuoyv2_watchtower_1
802a7c8cab78   iqtlabs/aisonobuoy-power:latest       "python3 /app.py "       36 minutes ago   Up 36 minutes              pibuoyv2_power_1
```

5. Check serial connection for AIS.
```
sudo screen /dev/serial0 38400
<press ESC> (you should see a menu)
<press ESC>
<ctrl>+a k
```
