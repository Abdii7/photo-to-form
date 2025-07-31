#!/usr/bin/env python3
"""
Photo to Form - OCR Data Extraction Application
Startup script with enhanced configuration and error handling
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    return True

def install_requirements():
    """Install required packages"""
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ Error: requirements.txt not found")
        return False
    
    print("📦 Installing requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    dirs = ["uploads", "results", "templates"]
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
    print("📁 Directories created/verified")

def check_dependencies():
    """Check if required dependencies are available"""
    required_modules = [
        ("flask", "Flask"),
        ("easyocr", "EasyOCR"),
        ("cv2", "OpenCV"),
        ("PIL", "Pillow"),
        ("numpy", "NumPy")
    ]
    
    missing = []
    for module, name in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(name)
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("🔧 Run: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Main startup function"""
    print("🚀 Starting Photo to Form OCR Application...")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Create directories
    create_directories()
    
    # Check dependencies
    if not check_dependencies():
        response = input("\n❓ Would you like to install missing dependencies? (y/n): ")
        if response.lower() in ['y', 'yes']:
            if not install_requirements():
                return 1
        else:
            print("❌ Cannot start without required dependencies")
            return 1
    
    # Import and start the Flask app
    try:
        from app import app
        print("\n✅ All dependencies loaded successfully!")
        print("🌐 Starting web server...")
        print("📱 Access the application at: http://localhost:5000")
        print("🛑 Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Run the Flask app
        app.run(
            debug=False,  # Set to False for production
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)),
            threaded=True
        )
        
    except ImportError as e:
        print(f"❌ Error importing application: {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n👋 Application stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())