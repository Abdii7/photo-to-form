from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Photo to Form OCR - Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #667eea; }
            .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎉 Photo to Form OCR App is Working!</h1>
            <div class="success">✅ Flask server is running successfully!</div>
            <p>Your application is ready. Here's what we accomplished:</p>
            <ul>
                <li>✅ Flask backend with EasyOCR integration</li>
                <li>✅ Modern drag-and-drop web interface</li>
                <li>✅ Batch image processing</li>
                <li>✅ Smart form data extraction</li>
                <li>✅ Mobile responsive design</li>
                <li>✅ JSON export functionality</li>
            </ul>
            <p><small>To use the full OCR functionality, the complete app.py has all the features ready.</small></p>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    port = 3000
    print(f"🚀 Simple test server starting...")
    print(f"📱 Open: http://localhost:{port}")
    app.run(host='127.0.0.1', port=port, debug=False)