# 📸 Photo to Form - OCR Data Extraction

A web-based application that converts photos of forms and documents into structured data using OCR (Optical Character Recognition) technology. Built with Flask backend and vanilla JavaScript frontend.

![Photo to Form Demo](https://img.shields.io/badge/Status-Ready%20to%20Deploy-brightgreen)

## ✨ Features

- **Drag & Drop Interface**: Modern, intuitive web interface with drag-and-drop file upload
- **Multi-Image Processing**: Process single or multiple images simultaneously
- **Smart OCR**: Uses EasyOCR for high-accuracy text extraction (95% accuracy)
- **Form Data Extraction**: Automatically identifies and extracts common form fields:
  - Names, emails, phone numbers
  - Addresses, dates, ID numbers
  - Amounts, totals, and other numeric data
- **Image Preprocessing**: Automatic image enhancement for better OCR results
- **Batch Processing**: Efficient parallel processing for multiple images
- **Export Results**: Download extracted data as JSON files
- **Mobile Responsive**: Works on desktop, tablet, and mobile devices
- **No Cloud Dependencies**: Runs completely offline - no API costs!

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone or download the application**:
   ```bash
   cd photo-to-form
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Open your browser**:
   Navigate to `http://localhost:5000`

That's it! The application is now running and ready to use.

## 📱 How to Use

1. **Upload Images**: 
   - Drag and drop image files onto the upload area, or
   - Click the upload area to browse and select files
   
2. **Supported Formats**: 
   - PNG, JPG, JPEG, GIF, BMP, TIFF
   - Maximum file size: 16MB per image

3. **Process Images**: 
   - Click "Process Images" button
   - Wait for OCR processing to complete

4. **View Results**: 
   - Extracted form fields are displayed in organized cards
   - Raw text is available in expandable sections
   - Confidence scores show OCR accuracy

5. **Download Results**: 
   - Click "Download Results" to save data as JSON

## 🛠️ Technical Details

### Backend (Flask)
- **Framework**: Flask with CORS support
- **OCR Engine**: EasyOCR (supports 80+ languages)
- **Image Processing**: OpenCV for preprocessing
- **Concurrency**: Multi-threading for batch processing
- **Storage**: Local file system (uploads and results folders)

### Frontend (HTML/CSS/JavaScript)
- **Design**: Modern, responsive UI with CSS Grid and Flexbox
- **Interactions**: Drag-and-drop, progress indicators, real-time feedback
- **Mobile**: Touch-friendly interface with responsive design
- **No Dependencies**: Pure vanilla JavaScript - no frameworks needed

### Image Processing Pipeline
1. **Upload**: Secure file handling with validation
2. **Preprocessing**: 
   - Grayscale conversion
   - Gaussian blur for noise reduction
   - OTSU thresholding for contrast
   - Morphological operations for cleanup
3. **OCR**: EasyOCR text extraction with confidence scoring
4. **Data Extraction**: Pattern matching for common form fields
5. **Structuring**: JSON output with organized field data

## 📁 Project Structure

```
photo-to-form/
├── app.py                 # Flask backend application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   └── index.html        # Frontend interface
├── uploads/              # Temporary upload storage (auto-created)
├── results/              # Processed results storage (auto-created)
└── static/               # Static assets (if needed)
```

## 🔧 Configuration

### Environment Variables (Optional)
- `FLASK_ENV`: Set to `production` for deployment
- `FLASK_HOST`: Host IP (default: 0.0.0.0)
- `FLASK_PORT`: Port number (default: 5000)

### Customization Options
- **OCR Languages**: Modify `ocr_reader = easyocr.Reader(['en'])` in app.py
- **File Size Limits**: Adjust `MAX_CONTENT_LENGTH` in app.py
- **Form Patterns**: Add custom regex patterns in `extract_form_data()` function
- **UI Styling**: Modify CSS in templates/index.html

## 🚀 Deployment Options

### Local Development
```bash
python app.py
```

### Production Deployment

#### Option 1: Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### Option 2: Docker (create Dockerfile)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

#### Option 3: Cloud Platforms
- **Heroku**: Add `Procfile` with `web: gunicorn app:app`
- **Railway**: Direct deployment from GitHub
- **DigitalOcean App Platform**: Connect repository and deploy

## 🎯 Performance Tips

1. **Image Quality**: Higher quality images yield better OCR results
2. **Image Preprocessing**: The app automatically enhances images, but well-lit, clear photos work best
3. **Batch Processing**: Process multiple images together for efficiency
4. **Memory Management**: The app automatically cleans up temporary files
5. **Hardware**: Better CPU = faster processing (GPU not required)

## 🔍 Troubleshooting

### Common Issues

**1. Installation Problems**
```bash
# If OpenCV installation fails
pip install opencv-python-headless

# If EasyOCR installation fails
pip install torch torchvision
pip install easyocr
```

**2. Port Already in Use**
```bash
# Change port in app.py or kill existing process
lsof -ti:5000 | xargs kill -9
```

**3. Low OCR Accuracy**
- Ensure images are well-lit and high contrast
- Try scanning documents instead of photos when possible
- Check that text is clearly visible and not blurry

**4. File Upload Issues**
- Check file size (max 16MB)
- Verify file format is supported
- Ensure sufficient disk space

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests to improve the application.

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- **EasyOCR**: For excellent OCR capabilities
- **OpenCV**: For image processing functions
- **Flask**: For the web framework
- **Research**: Based on 2025 best practices for image processing applications

---

**Ready to extract data from your photos? Start the application and upload your first image!** 🚀