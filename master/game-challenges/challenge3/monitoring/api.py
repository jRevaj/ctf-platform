#!/usr/bin/env python3
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
import json
import os

app = Flask(__name__)
CORS(app)
auth = HTTPBasicAuth()

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Admin users (with hardcoded credentials)
users = {
    "admin": "admin123",
    "system": "systempassword",
}

# Validate user credentials
@auth.verify_password
def verify_password(username, password):
    if username in users and users[username] == password:
        return username
    return None

# Insecure endpoint - auth bypass via header
@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    # Auth bypass: if X-Internal-Request header is set to "True",
    # skip authentication
    if request.headers.get('X-Internal-Request') == 'True':
        return jsonify({
            "status": "success",
            "metrics": {
                "cpu_usage": 42.5,
                "memory_usage": 3210,
                "disk_usage": 68.7,
                "network_traffic": 1024,
                "active_users": 15
            }
        })
    
    # Otherwise, require authentication
    if not request.authorization or not verify_password(
            request.authorization.username, 
            request.authorization.password):
        return jsonify({
            "status": "error",
            "message": "Authentication required"
        }), 401
    
    return jsonify({
        "status": "success",
        "metrics": {
            "cpu_usage": 42.5,
            "memory_usage": 3210,
            "disk_usage": 68.7,
            "network_traffic": 1024,
            "active_users": 15
        }
    })

# Insecure endpoint with flag - IDOR vulnerability
@app.route('/api/system/<system_id>', methods=['GET'])
@auth.login_required
def get_system(system_id):
    # Insecure direct object reference - no validation on system_id
    systems = {
        "1": {"name": "Web server", "status": "running"},
        "2": {"name": "File server", "status": "running"},
        "3": {"name": "Database server", "status": "running"},
        "admin": {"name": "Admin backend", "status": "running", "flag": "FLAG_PLACEHOLDER_6"}
    }
    
    if system_id in systems:
        return jsonify({
            "status": "success",
            "system": systems[system_id]
        })
    else:
        return jsonify({
            "status": "error",
            "message": "System not found"
        }), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090, debug=False)
