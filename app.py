from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import easyocr
import cv2
import numpy as np
import json
import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename
import concurrent.futures
from PIL import Image
import io
import base64

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Initialize EasyOCR reader (supports English by default)
ocr_reader = easyocr.Reader(['en'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image_path):
    """Preprocess image for better OCR results"""
    image = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply threshold to get better contrast
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Morphological operations to clean up the image
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    return processed

def extract_form_data(ocr_results):
    """Extract structured form data from OCR results"""
    text_blocks = []
    
    # Extract all text with coordinates
    for (bbox, text, confidence) in ocr_results:
        if confidence > 0.5:  # Filter low confidence results
            text_blocks.append({
                'text': text.strip(),
                'confidence': confidence,
                'bbox': bbox
            })
    
    # Sort by y-coordinate (top to bottom)
    text_blocks.sort(key=lambda x: x['bbox'][0][1])
    
    # Common form fields patterns
    form_patterns = {
        'name': r'(?i)(name|full name|first name|last name)[:\s]*([a-zA-Z\s]+)',
        'email': r'(?i)(email|e-mail)[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        'phone': r'(?i)(phone|mobile|tel)[:\s]*([+]?[\d\s\-\(\)]{10,})',
        'address': r'(?i)(address|addr)[:\s]*([a-zA-Z0-9\s,.-]+)',
        'date': r'(?i)(date|dob|birth)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        'number': r'(?i)(number|no|id)[:\s]*([a-zA-Z0-9]+)',
        'amount': r'(?i)(amount|total|sum|price)[:\s]*[\$]?(\d+\.?\d*)',
    }
    
    # Extract form fields
    form_data = {}
    all_text = ' '.join([block['text'] for block in text_blocks])
    
    # Try to match patterns
    for field, pattern in form_patterns.items():
        matches = re.findall(pattern, all_text)
        if matches:
            form_data[field] = matches[0][1] if isinstance(matches[0], tuple) else matches[0]
    
    # Extract key-value pairs (field: value format)
    for block in text_blocks:
        text = block['text']
        if ':' in text:
            parts = text.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip().lower().replace(' ', '_')
                value = parts[1].strip()
                if value:
                    form_data[key] = value
    
    return {
        'extracted_fields': form_data,
        'raw_text': all_text,
        'text_blocks': text_blocks,
        'timestamp': datetime.now().isoformat(),
        'total_confidence': sum([block['confidence'] for block in text_blocks]) / len(text_blocks) if text_blocks else 0
    }

def process_single_image(image_path):
    """Process a single image and extract form data"""
    try:
        # Preprocess image
        processed_image = preprocess_image(image_path)
        
        # Perform OCR
        ocr_results = ocr_reader.readtext(processed_image)
        
        # Extract form data
        form_data = extract_form_data(ocr_results)
        
        return {
            'success': True,
            'data': form_data,
            'filename': os.path.basename(image_path)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'filename': os.path.basename(image_path)
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    
    if not files or all(file.filename == '' for file in files):
        return jsonify({'error': 'No files selected'}), 400
    
    results = []
    valid_files = []
    
    # Save uploaded files
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            valid_files.append(file_path)
    
    if not valid_files:
        return jsonify({'error': 'No valid image files provided'}), 400
    
    # Process images (can be parallelized for multiple images)
    if len(valid_files) == 1:
        # Single file processing
        result = process_single_image(valid_files[0])
        results.append(result)
    else:
        # Batch processing with threading
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {executor.submit(process_single_image, file_path): file_path 
                            for file_path in valid_files}
            
            for future in concurrent.futures.as_completed(future_to_file):
                result = future.result()
                results.append(result)
    
    # Save results
    result_filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    result_path = os.path.join(app.config['RESULTS_FOLDER'], result_filename)
    
    with open(result_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Clean up uploaded files (optional)
    for file_path in valid_files:
        try:
            os.remove(file_path)
        except OSError:
            pass
    
    return jsonify({
        'success': True,
        'results': results,
        'result_file': result_filename,
        'total_processed': len(results)
    })

@app.route('/results/<filename>')
def get_results(filename):
    """Retrieve saved results"""
    try:
        result_path = os.path.join(app.config['RESULTS_FOLDER'], filename)
        with open(result_path, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({'error': 'Results not found'}), 404

@app.route('/download/<filename>')
def download_results(filename):
    """Download results as JSON file"""
    return send_from_directory(app.config['RESULTS_FOLDER'], filename, as_attachment=True)

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'ocr_ready': True})

if __name__ == '__main__':
    print("Starting Photo-to-Form OCR Application...")
    print("Access the application at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)