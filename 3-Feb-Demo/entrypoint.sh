#!/bin/bash
if [ "$ROLE" == "controller" ]; then
    echo "Starting Controller..."
    python controller.py
elif [ "$ROLE" == "collector" ]; then
    echo "Starting Collector..."
    python collector.py
else
    echo "Please set ROLE environment variable to 'controller' or 'collector'"
    exit 1
fi
