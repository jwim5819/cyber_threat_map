#!/usr/bin/env bash

# Start redis-server
systemctl start redis.service

# Start the DataServer
cd ./data_server
nohup python3 ./data_server.py > /dev/null 2>&1 & 

# Start the Fake Syslog Gen Script
nohup python3 ./random_syslog_gen.py  > /dev/null 2>&1 &
cd ..

# Start the Map Server
cd ./map_server
# nohup python3 ./map_server.py &
python3 ./map_server.py
