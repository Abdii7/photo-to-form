#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import easyocr
import cv2
import numpy as np
import os
import json
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image
import io

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

# Initialize EasyOCR reader
print("🤖 Initializing EasyOCR... This may take a moment on first run.")
try:
    ocr_reader = easyocr.Reader(['en'])
    print("✅ EasyOCR ready!")
except Exception as e:
    print(f"❌ EasyOCR initialization failed: {e}")
    ocr_reader = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_form_data(ocr_results):
    """Extract structured form data from OCR results"""
    if not ocr_results:
        return {
            'extracted_fields': {},
            'raw_text': '',
            'text_blocks': [],
            'timestamp': datetime.now().isoformat(),
            'total_confidence': 0.0
        }
    
    text_blocks = []
    
    # Extract all text with confidence
    for (bbox, text, confidence) in ocr_results:
        if confidence > 0.3:  # Lower threshold for better extraction
            # Convert NumPy types to Python native types for JSON serialization
            text_blocks.append({
                'text': str(text).strip(),
                'confidence': float(confidence),
                'bbox': [[float(point[0]), float(point[1])] for point in bbox]
            })
    
    # Sort by y-coordinate (top to bottom)
    text_blocks.sort(key=lambda x: x['bbox'][0][1])
    
    # Combine all text
    all_text = ' '.join([block['text'] for block in text_blocks])
    
    # Common form fields patterns
    form_patterns = {
        'name': r'(?i)(name|full name|first name|last name)[:\s]*([a-zA-Z\s]{2,30})',
        'email': r'(?i)(email|e-mail)[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        'phone': r'(?i)(phone|mobile|tel|call)[:\s]*([+]?[\d\s\-\(\)]{10,})',
        'address': r'(?i)(address|addr)[:\s]*([a-zA-Z0-9\s,.-]{5,50})',
        'date': r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        'number': r'(?i)(number|no|id)[:\s]*([a-zA-Z0-9]{3,})',
        'amount': r'(?i)(amount|total|sum|price|cost|pay)[:\s]*[\$]?(\d+\.?\d*)',
        'company': r'(?i)(company|business|corp|inc|ltd)[:\s]*([a-zA-Z\s&]{3,30})',
    }
    
    # Extract form fields
    form_data = {}
    
    # Try to match patterns in the full text
    for field, pattern in form_patterns.items():
        matches = re.findall(pattern, all_text)
        if matches:
            # Take the first match and clean it
            if isinstance(matches[0], tuple):
                value = matches[0][1].strip()
            else:
                value = matches[0].strip()
            
            if value and len(value) > 1:
                form_data[field] = value
    
    # Also look for key-value pairs (field: value format)
    lines = all_text.split()
    for i, word in enumerate(lines):
        if ':' in word and i < len(lines) - 1:
            key = word.replace(':', '').strip().lower()
            value = lines[i + 1].strip()
            if len(key) > 1 and len(value) > 1:
                form_data[key] = value
    
    # Look for email patterns anywhere in text
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, all_text)
    if emails:
        form_data['email'] = emails[0]
    
    # Look for phone patterns
    phone_pattern = r'[\+]?[\d\s\-\(\)]{10,}'
    phones = re.findall(phone_pattern, all_text)
    if phones:
        form_data['phone'] = phones[0].strip()
    
    return {
        'extracted_fields': form_data,
        'raw_text': str(all_text),
        'text_blocks': text_blocks,
        'timestamp': datetime.now().isoformat(),
        'total_confidence': float(sum([block['confidence'] for block in text_blocks]) / len(text_blocks)) if text_blocks else 0.0
    }

def process_image_ocr(image_path):
    """Process image with OCR"""
    if not ocr_reader:
        return {
            'success': False,
            'error': 'OCR reader not initialized',
            'filename': os.path.basename(image_path)
        }
    
    try:
        print(f"🔍 Processing: {os.path.basename(image_path)}")
        
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            return {
                'success': False,
                'error': 'Could not read image file',
                'filename': os.path.basename(image_path)
            }
        
        # Convert to RGB for EasyOCR
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Perform OCR
        print("🤖 Running OCR...")
        ocr_results = ocr_reader.readtext(image_rgb)
        print(f"📝 Found {len(ocr_results)} text regions")
        
        # Extract form data
        form_data = extract_form_data(ocr_results)
        
        return {
            'success': True,
            'data': form_data,
            'filename': os.path.basename(image_path)
        }
        
    except Exception as e:
        print(f"❌ OCR Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'filename': os.path.basename(image_path)
        }

@app.route('/')
def serve_interface():
    return send_from_directory('.', 'full_interface.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        print("📸 Processing upload request...")
        
        if not ocr_reader:
            return jsonify({'error': 'OCR system not available. Please restart the application.'}), 500
        
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
                unique_filename = f"{timestamp}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                
                # Save file
                file.save(file_path)
                
                # Process with OCR
                result = process_image_ocr(file_path)
                results.append(result)
                
                # Clean up uploaded file
                try:
                    os.remove(file_path)
                except:
                    pass
        
        print(f"✅ Processed {len(results)} files")
        
        return jsonify({
            'success': True,
            'results': results,
            'total_processed': len(results)
        })
        
    except Exception as e:
        print(f"❌ Upload Error: {str(e)}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy', 
        'app': 'Photo to Form OCR', 
        'ocr_ready': ocr_reader is not None
    })

if __name__ == '__main__':
    print("🚀 Starting Photo to Form OCR Application...")
    print("🤖 Real OCR processing with EasyOCR")
    print("📱 Upload images to extract actual text!")
    print("=" * 60)
    
    # Find free port
    import socket
    def find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    port = find_free_port()
    
    # Open browser
    import threading
    import time
    import webbrowser
    
    def open_browser():
        time.sleep(2)
        webbrowser.open(f'http://localhost:{port}')
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    print(f"🌐 Server running at: http://localhost:{port}")
    app.run(host='127.0.0.1', port=port, debug=False)