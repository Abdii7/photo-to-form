#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import base64

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def serve_interface():
    return send_from_directory('.', 'full_interface.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        print("📸 Processing upload request...")
        
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        
        if not files or all(file.filename == '' for file in files):
            return jsonify({'error': 'No files selected'}), 400
        
        results = []
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Simulate OCR processing (demo data)
                demo_result = {
                    'success': True,
                    'filename': file.filename,
                    'data': {
                        'extracted_fields': {
                            'name': 'John Smith',
                            'email': 'john.smith@example.com',
                            'phone': '(555) 123-4567',
                            'date': '01/15/2024',
                            'amount': '$299.99',
                            'company': 'Demo Company Inc.'
                        },
                        'raw_text': 'DEMO: This is simulated OCR text extraction. In the full version, this would contain the actual extracted text from your image.',
                        'total_confidence': 0.92,
                        'timestamp': datetime.now().isoformat()
                    }
                }
                results.append(demo_result)
                
                # Clean up uploaded file
                try:
                    os.remove(file_path)
                except:
                    pass
        
        print(f"✅ Processed {len(results)} files successfully")
        
        return jsonify({
            'success': True,
            'results': results,
            'total_processed': len(results),
            'message': 'Demo processing complete! This shows how the full OCR would work.'
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'app': 'Photo to Form OCR Demo'})

if __name__ == '__main__':
    print("🚀 Starting Photo to Form OCR Demo Server...")
    print("📱 The app will open automatically in your browser")
    print("🎯 Upload images and click 'Process Images' to see demo results!")
    print("=" * 60)
    
    # Try to find a free port
    import socket
    def find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    port = find_free_port()
    
    # Open browser automatically
    import threading
    import time
    import webbrowser
    
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(f'http://localhost:{port}')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    print(f"🌐 Server running at: http://localhost:{port}")
    app.run(host='127.0.0.1', port=port, debug=False)