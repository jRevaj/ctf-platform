from flask import Flask, jsonify
import requests
import os
import socket

app = Flask(__name__)

# More robust target1 host resolution
TARGET1_HOST = os.getenv('TARGET1_HOST', 'target1')
TARGET3_HOST = os.getenv('TARGET3_HOST', 'target3')

# Log the host we're using
print(f"Starting Flask app with TARGET1_HOST: {TARGET1_HOST}")
print(f"Attempting to connect to: http://{TARGET1_HOST}:8080")
print(f"Starting Flask app with TARGET3_HOST: {TARGET3_HOST}")
print(f"Attempting to connect to: http://{TARGET3_HOST}:8080")


@app.route('/')
def index():
    return jsonify({
        'message': 'Welcome to the flag service',
        'target1_host': TARGET1_HOST,
        'target3_host': TARGET3_HOST
    })

@app.route('/target1')
def target1_flag():
    try:
        response = requests.get(f'http://{TARGET1_HOST}:8080/flag')
        if response.status_code == 200:
            return jsonify({'flag': response.text.strip()})
        else:
            return jsonify({'error': f'Failed to get flag from target1: {response.status_code}'}), 500
    except Exception as e:
        error_msg = str(e)
        print(f"Error in target1_flag: {error_msg}")        
        try:
            target_ip = socket.gethostbyname('target1')
            print(f"Resolved target1 to: {target_ip}")            
            try:
                response = requests.get(f'http://{target_ip}:8080/flag')
                if response.status_code == 200:
                    return jsonify({'flag': response.text.strip()})
                else:
                    return jsonify({'error': f'Failed with resolved IP {target_ip}: {response.status_code}'}), 500
            except Exception as e2:
                return jsonify({'error': f'Original error: {error_msg}. Retry with IP {target_ip} failed: {str(e2)}'}), 500
        except Exception as e3:
            return jsonify({'error': f'Original error: {error_msg}. Manual resolution failed: {str(e3)}'}), 500


@app.route('/target3')
def target3_flag():
    try:
        response = requests.get(f'http://{TARGET3_HOST}:8080/flag')
        if response.status_code == 200:
            return jsonify({'flag': response.text.strip()})
        else:
            return jsonify({'error': f'Failed to get flag from target3: {response.status_code}'}), 500
    except Exception as e:
        error_msg = str(e)
        print(f"Error in target3_flag: {error_msg}")        
        try:
            target_ip = socket.gethostbyname('target3')
            print(f"Resolved target3 to: {target_ip}")            
            try:
                response = requests.get(f'http://{target_ip}:8080/flag')
                if response.status_code == 200:
                    return jsonify({'flag': response.text.strip()})
                else:
                    return jsonify({'error': f'Failed with resolved IP {target_ip}: {response.status_code}'}), 500
            except Exception as e2:
                return jsonify({'error': f'Original error: {error_msg}. Retry with IP {target_ip} failed: {str(e2)}'}), 500
        except Exception as e3:
            return jsonify({'error': f'Original error: {error_msg}. Manual resolution failed: {str(e3)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 