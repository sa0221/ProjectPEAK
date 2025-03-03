#!/bin/bash
if [ "$ROLE" == "controller" ]; then
    echo "Starting Controller..."
    exec python controller.py
elif [ "$ROLE" == "collector" ]; then
    echo "Starting Collector..."
    exec python collector.py
else
    echo "Please set ROLE environment variable to 'controller' or 'collector'"
    exit 1
fi
