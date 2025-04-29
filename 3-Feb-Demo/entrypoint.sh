#!/bin/bash
#
# Shared entrypoint for both controller & collector.
# ROLE must be set (via docker-compose.yml) to either "controller" or "collector".

if [ "$ROLE" == "controller" ]; then
    echo "🚀 Starting Controller…"
    exec python controller.py

elif [ "$ROLE" == "collector" ]; then
    echo "📡 Starting Collector…"
    exec python collector.py

else
    echo "❌ ROLE must be set to 'controller' or 'collector'"
    exit 1
fi
