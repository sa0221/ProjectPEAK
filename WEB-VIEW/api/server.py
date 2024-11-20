from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import subprocess
import threading
import json
import os
import time
from datetime import datetime

app = Flask(__name__, static_folder='../dist')
CORS(app)

# Global variables
collection_process = None
is_collecting = False
collection_thread = None

def run_collection_script():
    global is_collecting
    while is_collecting:
        try:
            # Run the collection script and capture output
            result = subprocess.run(['python3', 'collector.py'], 
                                 capture_output=True, 
                                 text=True, 
                                 timeout=10)
            print(result.stdout)
        except subprocess.TimeoutExpired:
            print("Collection cycle completed")
        except Exception as e:
            print(f"Error in collection: {e}")
        time.sleep(1)

@app.route('/')
def serve_app():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/start', methods=['POST'])
def start_collection():
    global is_collecting, collection_thread
    
    if not is_collecting:
        is_collecting = True
        collection_thread = threading.Thread(target=run_collection_script)
        collection_thread.start()
        return jsonify({"status": "Collection started"})
    return jsonify({"status": "Collection already running"})

@app.route('/api/stop', methods=['POST'])
def stop_collection():
    global is_collecting, collection_thread
    
    if is_collecting:
        is_collecting = False
        if collection_thread:
            collection_thread.join()
        return jsonify({"status": "Collection stopped"})
    return jsonify({"status": "Collection not running"})

@app.route('/api/reset', methods=['POST'])
def reset_data():
    try:
        with open('project_peak_signals.csv', 'w') as f:
            f.write("Timestamp,Type,Name/Address,Signal Strength,Additional Info\n")
        return jsonify({"status": "Data reset successful"})
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500

@app.route('/api/save', methods=['POST'])
def save_data():
    try:
        # Create a backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f'project_peak_signals_{timestamp}.csv'
        os.system(f'cp project_peak_signals.csv {backup_file}')
        return jsonify({
            "status": "success",
            "message": f"Data saved to {backup_file}"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/data', methods=['GET'])
def get_data():
    try:
        # Read the last 100 lines from the CSV file
        with open('project_peak_signals.csv', 'r') as f:
            lines = f.readlines()[-100:]  # Get last 100 lines
            
        data = []
        headers = ['timestamp', 'type', 'name_address', 'signal_strength', 'additional_info']
        
        for line in lines[1:]:  # Skip header
            values = line.strip().split(',')
            data.append(dict(zip(headers, values)))
            
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)