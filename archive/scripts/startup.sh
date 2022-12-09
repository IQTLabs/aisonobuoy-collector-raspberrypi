#!/bin/bash
timeout 60 /opt/AISonobuoy/PiBuoy/scripts/gps.sh
if [ $? -eq 1 ]
then
  logger "Failed to bring up GPS, trying one more time"
  timeout 60 /opt/AISonobuoy/PiBuoy/scripts/gps.sh
  if [ $? -eq 1 ]
  then
    logger "Last attempt to bring up GPS failed"
  fi
fi
# do this twice, sometimes it doesn't take the first time
timeout 10 stty -F /dev/serial0 speed 38400
timeout 10 stty -F /dev/serial0 speed 38400
timeout 10 stty -F /dev/ttyUSB1 speed 9600
timeout 10 gpsd -n /dev/ttyUSB1 -F /var/run/gpsd.sock
mkdir -p /flash/telemetry/pindrop
mkdir -p /flash/telemetry/hydrophone
amixer -D sysdefault cset name='ADC Capture Volume' 96,96
