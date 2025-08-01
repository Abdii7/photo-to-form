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
from PIL import Image, ImageEnhance, ImageFilter
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

def preprocess_image(image_path):
    """Advanced image preprocessing for better OCR results"""
    try:
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            return None
        
        # Convert to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL for additional processing
        pil_image = Image.fromarray(image_rgb)
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(pil_image)
        pil_image = enhancer.enhance(1.5)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(pil_image)
        pil_image = enhancer.enhance(1.3)
        
        # Convert back to OpenCV format
        enhanced_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Apply adaptive threshold for better text extraction
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Apply morphological operations to clean up
        kernel = np.ones((1, 1), np.uint8)
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Convert back to RGB for EasyOCR
        processed_rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
        
        return processed_rgb
        
    except Exception as e:
        print(f"⚠️ Preprocessing failed: {e}, using original image")
        # Fallback to original image
        image = cv2.imread(image_path)
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image is not None else None

def extract_form_data(ocr_results):
    """Enhanced form data extraction with better pattern matching"""
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
        if confidence > 0.2:  # Lower threshold for more text
            # Convert NumPy types to Python native types for JSON serialization
            text_blocks.append({
                'text': str(text).strip(),
                'confidence': float(confidence),
                'bbox': [[float(point[0]), float(point[1])] for point in bbox]
            })
    
    # Sort by y-coordinate (top to bottom) then x-coordinate (left to right)
    text_blocks.sort(key=lambda x: (x['bbox'][0][1], x['bbox'][0][0]))
    
    # Combine all text
    all_text = ' '.join([block['text'] for block in text_blocks])
    
    # Enhanced form field patterns
    form_patterns = {
        'first_name': r'(?i)(first\s*name|given\s*name)[:\s]*([a-zA-Z]{2,20})',
        'last_name': r'(?i)(last\s*name|surname|family\s*name)[:\s]*([a-zA-Z]{2,20})',
        'full_name': r'(?i)(full\s*name|name)[:\s]*([a-zA-Z\s]{3,40})',
        'email': r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        'phone': r'(?i)(phone|mobile|tel|call)[:\s]*([+]?[\d\s\-\(\)]{10,})',
        'address': r'(?i)(address|addr)[:\s]*([a-zA-Z0-9\s,.-]{10,80})',
        'city': r'(?i)(city)[:\s]*([a-zA-Z\s]{2,30})',
        'state': r'(?i)(state|province)[:\s]*([a-zA-Z\s]{2,20})',
        'zip': r'(?i)(zip|postal)[:\s]*([a-zA-Z0-9\s\-]{3,10})',
        'date_of_birth': r'(?i)(date\s*of\s*birth|dob|birth\s*date)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        'date': r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        'ssn': r'(?i)(ssn|social\s*security)[:\s]*(\d{3}[-\s]?\d{2}[-\s]?\d{4})',
        'id_number': r'(?i)(id|number|no)[:\s]*([a-zA-Z0-9]{3,})',
        'amount': r'(?i)(amount|total|sum|price|cost|pay)[:\s]*[\$]?(\d+\.?\d*)',
        'company': r'(?i)(company|business|employer|corp|inc|ltd)[:\s]*([a-zA-Z\s&\.]{3,40})',
        'title': r'(?i)(title|position|job)[:\s]*([a-zA-Z\s]{3,30})',
        'department': r'(?i)(department|dept)[:\s]*([a-zA-Z\s]{3,30})',
    }
    
    # Extract form fields
    form_data = {}
    
    # Try to match patterns in the full text
    for field, pattern in form_patterns.items():
        matches = re.findall(pattern, all_text)
        if matches:
            # Take the first valid match
            for match in matches:
                if isinstance(match, tuple):
                    value = match[1].strip() if len(match) > 1 else match[0].strip()
                else:
                    value = match.strip()
                
                if value and len(value) > 1 and not value.isspace():
                    form_data[field] = value
                    break
    
    # Look for standalone email addresses
    email_pattern = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    emails = re.findall(email_pattern, all_text)
    if emails and 'email' not in form_data:
        form_data['email'] = emails[0]
    
    # Look for standalone phone numbers
    phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
    phones = re.findall(phone_pattern, all_text)
    if phones and 'phone' not in form_data:
        form_data['phone'] = phones[0].strip()
    
    # Look for dollar amounts
    money_pattern = r'\$\d+(?:\.\d{2})?'
    amounts = re.findall(money_pattern, all_text)
    if amounts and 'amount' not in form_data:
        form_data['amount'] = amounts[0]
    
    # Look for dates
    date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    dates = re.findall(date_pattern, all_text)
    if dates and 'date' not in form_data:
        form_data['date'] = dates[0]
    
    # Try to extract key-value pairs from nearby text blocks
    for i, block in enumerate(text_blocks):
        text = block['text'].lower()
        
        # Check if this block contains a field label
        for field_name in ['name', 'email', 'phone', 'address', 'date', 'company']:
            if field_name in text and ':' in text:
                # Look for value in same block or next block
                if i + 1 < len(text_blocks):
                    next_block = text_blocks[i + 1]
                    potential_value = next_block['text'].strip()
                    if potential_value and len(potential_value) > 1:
                        form_data[field_name] = potential_value
    
    return {
        'extracted_fields': form_data,
        'raw_text': str(all_text),
        'text_blocks': text_blocks,
        'timestamp': datetime.now().isoformat(),
        'total_confidence': float(sum([block['confidence'] for block in text_blocks]) / len(text_blocks)) if text_blocks else 0.0
    }

def process_image_ocr(image_path):
    """Process image with enhanced OCR"""
    if not ocr_reader:
        return {
            'success': False,
            'error': 'OCR reader not initialized',
            'filename': os.path.basename(image_path)
        }
    
    try:
        print(f"🔍 Processing: {os.path.basename(image_path)}")
        
        # Preprocess image for better OCR
        processed_image = preprocess_image(image_path)
        if processed_image is None:
            return {
                'success': False,
                'error': 'Could not process image file',
                'filename': os.path.basename(image_path)
            }
        
        # Perform OCR with different configurations for better results
        print("🤖 Running enhanced OCR...")
        
        # Try with default settings first
        ocr_results = ocr_reader.readtext(processed_image, detail=1)
        
        # If low confidence, try with different settings
        if not ocr_results or sum([conf for _, _, conf in ocr_results]) / len(ocr_results) < 0.5:
            print("🔄 Trying with enhanced settings...")
            # Try with original image too
            original_image = cv2.imread(image_path)
            if original_image is not None:
                original_rgb = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
                ocr_results_orig = ocr_reader.readtext(original_rgb, detail=1)
                
                # Combine results from both attempts
                ocr_results.extend(ocr_results_orig)
        
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
                
                # Process with enhanced OCR
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
        'app': 'Enhanced Photo to Form OCR', 
        'ocr_ready': ocr_reader is not None
    })

if __name__ == '__main__':
    print("🚀 Starting Enhanced Photo to Form OCR Application...")
    print("🤖 Real OCR processing with image enhancement")
    print("📱 Upload images to extract better text!")
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