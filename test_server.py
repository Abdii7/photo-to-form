#!/usr/bin/env python3
"""
Quick test server to verify the Photo to Form app is working
"""

from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return {'status': 'healthy', 'message': 'Photo to Form OCR App is running!'}

if __name__ == '__main__':
    import socket
    def find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    port = find_free_port()
    print("🚀 Starting Photo to Form Test Server...")
    print(f"📱 Open your browser and go to: http://localhost:{port}")
    print("🛑 Press Ctrl+C to stop")
    
    app.run(debug=True, host='127.0.0.1', port=port)