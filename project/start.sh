#!/bin/bash

# Start the Flask API server
python3 api/server.py &

# Start the Vite server
npm run preview

# Wait for any process to exit
wait -n

# Exit with status of process that exited first
exit $?