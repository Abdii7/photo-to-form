#!/usr/bin/env python3
"""
Web-optimized version of Photo to Form OCR
Designed for cloud deployment platforms like Railway, Render, etc.
"""

from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
import easyocr
import cv2
import numpy as np
import os
import json
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from PIL import Image, ImageEnhance
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

# Initialize EasyOCR reader with error handling for web deployment
print("🤖 Initializing EasyOCR for web deployment...")
ocr_reader = None

def init_ocr():
    global ocr_reader
    try:
        ocr_reader = easyocr.Reader(['en'], gpu=False)  # Disable GPU for web deployment
        print("✅ EasyOCR ready for web!")
        return True
    except Exception as e:
        print(f"❌ EasyOCR initialization failed: {e}")
        return False

# Initialize OCR on startup
init_ocr()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_form_data(ocr_results):
    """Extract structured form data from OCR results"""
    if not ocr_results:
        return {
            'extracted_fields': {},
            'raw_text': 'No text detected in image',
            'text_blocks': [],
            'timestamp': datetime.now().isoformat(),
            'total_confidence': 0.0
        }
    
    text_blocks = []
    
    # Extract all text with confidence
    for (bbox, text, confidence) in ocr_results:
        if confidence > 0.2:
            text_blocks.append({
                'text': str(text).strip(),
                'confidence': float(confidence),
                'bbox': [[float(point[0]), float(point[1])] for point in bbox]
            })
    
    # Sort by position
    text_blocks.sort(key=lambda x: (x['bbox'][0][1], x['bbox'][0][0]))
    
    # Combine all text
    all_text = ' '.join([block['text'] for block in text_blocks])
    
    # Enhanced form field patterns
    form_patterns = {
        'name': r'(?i)(name)[:\s]*([a-zA-Z\s]{2,40})',
        'email': r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        'phone': r'(?i)(phone|tel)[:\s]*([+]?[\d\s\-\(\)]{10,})',
        'address': r'(?i)(address)[:\s]*([a-zA-Z0-9\s,.-]{5,50})',
        'date': r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        'amount': r'(?i)(amount|total|price)[:\s]*[\$]?(\d+\.?\d*)',
        'company': r'(?i)(company|business)[:\s]*([a-zA-Z\s&]{3,30})',
    }
    
    # Extract form fields
    form_data = {}
    
    for field, pattern in form_patterns.items():
        matches = re.findall(pattern, all_text)
        if matches:
            for match in matches:
                if isinstance(match, tuple):
                    value = match[1].strip() if len(match) > 1 else match[0].strip()
                else:
                    value = match.strip()
                
                if value and len(value) > 1:
                    form_data[field] = value
                    break
    
    # Look for standalone patterns
    email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    emails = re.findall(email_pattern, all_text)
    if emails and 'email' not in form_data:
        form_data['email'] = emails[0]
    
    phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
    phones = re.findall(phone_pattern, all_text)
    if phones and 'phone' not in form_data:
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
            'error': 'OCR system not available',
            'filename': os.path.basename(image_path)
        }
    
    try:
        print(f"🔍 Processing: {os.path.basename(image_path)}")
        
        # Read and process image
        image = cv2.imread(image_path)
        if image is None:
            return {
                'success': False,
                'error': 'Could not read image file',
                'filename': os.path.basename(image_path)
            }
        
        # Convert to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Perform OCR
        print("🤖 Running OCR...")
        ocr_results = ocr_reader.readtext(image_rgb, detail=1)
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

# Web interface template
WEB_INTERFACE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Photo to Form - OCR Web App</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; padding: 20px;
        }
        .container {
            max-width: 1000px; margin: 0 auto; background: white;
            border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white; padding: 30px; text-align: center; border-radius: 20px 20px 0 0;
        }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .content { padding: 40px; }
        .upload-area {
            border: 3px dashed #667eea; border-radius: 15px;
            padding: 60px 40px; background: #f8f9ff; text-align: center;
            cursor: pointer; transition: all 0.3s ease;
        }
        .upload-area:hover {
            border-color: #764ba2; background: #f0f2ff; transform: translateY(-2px);
        }
        .upload-icon { font-size: 4rem; color: #667eea; margin-bottom: 20px; }
        .btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white; padding: 12px 30px; border: none;
            border-radius: 25px; font-size: 1rem; cursor: pointer; margin: 10px;
        }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .results { margin-top: 30px; display: none; }
        .result-card {
            background: #f8f9fa; border-radius: 15px; padding: 25px;
            margin: 15px 0; box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 10px; margin: 20px 0; }
        .hidden { display: none; }
        .web-badge {
            background: #28a745; color: white; padding: 8px 15px;
            border-radius: 20px; font-size: 0.9rem; margin: 10px 0;
            display: inline-block;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 Photo to Form OCR - Web App</h1>
            <p>Convert images to structured form data - Running on the web!</p>
            <div class="web-badge">✅ Web Deployed Version</div>
        </div>
        <div class="content">
            <div class="success">
                🎉 <strong>Your OCR Web App is Live!</strong><br>
                Upload images and extract structured data with real OCR processing.
            </div>

            <div class="upload-area" id="uploadArea">
                <div class="upload-icon">📸</div>
                <h3>Drop your images here or click to browse</h3>
                <p>Supports PNG, JPG, JPEG, GIF, BMP, TIFF (Max 16MB each)</p>
                <input type="file" id="fileInput" class="hidden" multiple accept="image/*">
            </div>

            <div style="text-align: center; margin: 20px 0;">
                <button class="btn" id="processBtn" disabled>🚀 Extract Data</button>
                <button class="btn" id="clearBtn">🗑️ Clear</button>
            </div>

            <div class="results" id="results">
                <h3>📋 Extracted Form Data:</h3>
                <div id="resultsContent"></div>
            </div>

            <div style="margin-top: 40px; padding: 20px; background: #e9ecef; border-radius: 15px;">
                <h3>🌐 Web App Features:</h3>
                <ul style="margin: 15px 0;">
                    <li>✅ Real OCR processing with EasyOCR</li>
                    <li>✅ Smart form field extraction</li>
                    <li>✅ Works on any device with internet</li>
                    <li>✅ No installation required</li>
                    <li>✅ Instant results</li>
                </ul>
                <p><strong>GitHub:</strong> <a href="https://github.com/Abdii7/photo-to-form">https://github.com/Abdii7/photo-to-form</a></p>
            </div>
        </div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const processBtn = document.getElementById('processBtn');
        const clearBtn = document.getElementById('clearBtn');
        const results = document.getElementById('results');
        const resultsContent = document.getElementById('resultsContent');

        let selectedFiles = [];

        uploadArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#28a745';
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#667eea';
            handleFiles(e.dataTransfer.files);
        });

        function handleFiles(files) {
            selectedFiles = Array.from(files).filter(file => 
                ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp', 'image/tiff'].includes(file.type)
            );
            processBtn.disabled = selectedFiles.length === 0;
            uploadArea.innerHTML = `
                <div class="upload-icon">✅</div>
                <h3>${selectedFiles.length} image(s) selected</h3>
                <p>Click "Extract Data" to process</p>
            `;
        }

        processBtn.addEventListener('click', async () => {
            if (selectedFiles.length === 0) return;

            processBtn.disabled = true;
            processBtn.textContent = '⏳ Processing...';

            const formData = new FormData();
            selectedFiles.forEach(file => formData.append('files', file));

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.success) {
                    displayResults(data.results);
                } else {
                    alert('Error: ' + (data.error || 'Processing failed'));
                }
            } catch (error) {
                alert('Network error: ' + error.message);
            } finally {
                processBtn.disabled = false;
                processBtn.textContent = '🚀 Extract Data';
            }
        });

        function displayResults(results) {
            results.style.display = 'block';
            resultsContent.innerHTML = '';

            results.forEach(result => {
                if (result.success) {
                    const data = result.data;
                    const confidence = Math.round(data.total_confidence * 100);
                    
                    const card = document.createElement('div');
                    card.className = 'result-card';
                    card.innerHTML = `
                        <h4>📄 ${result.filename} (${confidence}% confidence)</h4>
                        <div style="margin: 15px 0;">
                            <strong>Extracted Fields:</strong>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px; margin: 10px 0;">
                                ${Object.entries(data.extracted_fields).map(([key, value]) => 
                                    `<div style="background: white; padding: 10px; border-radius: 5px;">
                                        <strong>${key}:</strong> ${value}
                                    </div>`
                                ).join('')}
                            </div>
                        </div>
                        <details>
                            <summary style="cursor: pointer; font-weight: bold;">Raw Text</summary>
                            <div style="background: white; padding: 15px; border-radius: 5px; margin: 10px 0; font-family: monospace; font-size: 0.9rem;">
                                ${data.raw_text}
                            </div>
                        </details>
                    `;
                    resultsContent.appendChild(card);
                } else {
                    const errorCard = document.createElement('div');
                    errorCard.className = 'result-card';
                    errorCard.innerHTML = `
                        <h4>❌ ${result.filename}</h4>
                        <p style="color: #dc3545;">Error: ${result.error}</p>
                    `;
                    resultsContent.appendChild(errorCard);
                }
            });
        }

        clearBtn.addEventListener('click', () => {
            selectedFiles = [];
            fileInput.value = '';
            processBtn.disabled = true;
            results.style.display = 'none';
            uploadArea.innerHTML = `
                <div class="upload-icon">📸</div>
                <h3>Drop your images here or click to browse</h3>
                <p>Supports PNG, JPG, JPEG, GIF, BMP, TIFF (Max 16MB each)</p>
            `;
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(WEB_INTERFACE)

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        if not ocr_reader:
            return jsonify({'error': 'OCR system not available. Please wait for initialization.'}), 500
        
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
                
                file.save(file_path)
                result = process_image_ocr(file_path)
                results.append(result)
                
                # Clean up
                try:
                    os.remove(file_path)
                except:
                    pass
        
        return jsonify({
            'success': True,
            'results': results,
            'total_processed': len(results)
        })
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy', 
        'app': 'Photo to Form OCR Web App',
        'ocr_ready': ocr_reader is not None
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Starting Photo to Form OCR Web App on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)