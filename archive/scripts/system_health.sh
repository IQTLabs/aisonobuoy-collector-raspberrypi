#!/bin/bash

timestamp=$(date +%s%3N)
hostname=$(hostname)
output_dir=/flash/telemetry/system/"$hostname-$timestamp"
mkdir -p "$output_dir"

timeout 5 df > "$output_dir/$hostname-$timestamp"-df.txt
timeout 5 /usr/sbin/ifconfig -a > "$output_dir/$hostname-$timestamp"-ifconfig.txt
timeout 5 vcgencmd measure_temp > "$output_dir/$hostname-$timestamp"-temp.txt
timeout 5 vcgencmd measure_volts > "$output_dir/$hostname-$timestamp"-volts.txt
timeout 5 uptime > "$output_dir/$hostname-$timestamp"-uptime.txt
timeout 5 free > "$output_dir/$hostname-$timestamp"-mem.txt
timeout 10 raspinfo > "$output_dir/$hostname-$timestamp"-raspinfo.txt
timeout 10 cat /var/log/sleepypid.log > "$output_dir/$hostname-$timestamp"-sleepypid.txt
true > /var/log/sleepypid.log
