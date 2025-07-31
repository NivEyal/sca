#!/usr/bin/env python3
"""
Trading Strategy Scanner - Main Application Runner
Compatible with Python 3.7+
"""

import os
import sys
import subprocess
import webbrowser
import time
import threading
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def install_requirements():
    """Install required packages"""
    print("📦 Installing required packages...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade", "pip"
        ])
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Packages installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    required_modules = [
        'flask', 'pandas', 'numpy', 'plotly', 'requests',
        'streamlit', 'alpaca_trade_api'
    ]
    
    failed_imports = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"❌ Failed to import: {', '.join(failed_imports)}")
        return False
    
    print("✅ All imports successful")
    return True

def start_flask_server():
    """Start the Flask server"""
    print("🚀 Starting Flask server...")
    try:
        # Import and run server
        import server
        return True
    except Exception as e:
        print(f"❌ Failed to start Flask server: {e}")
        return False

def start_streamlit_app():
    """Start the Streamlit app"""
    print("🚀 Starting Streamlit app...")
    try:
        subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", "streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
        time.sleep(3)
        webbrowser.open("http://localhost:8501")
        return True
    except Exception as e:
        print(f"❌ Failed to start Streamlit: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Trading Strategy Scanner - Setup & Launch")
    print("=" * 60)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Ask user if they want to install requirements
    install = input("📦 Install/update required packages? (y/n): ").lower().strip()
    if install in ['y', 'yes', '']:
        if not install_requirements():
            return
    
    # Test imports
    if not test_imports():
        print("❌ Some imports failed. Please install missing packages.")
        return
    
    print("\n🎯 Choose your preferred interface:")
    print("1. 🌐 Web App (Flask + HTML/CSS/JS)")
    print("2. 📊 Streamlit App (Python Dashboard)")
    print("3. 🧪 Test Connection Only")
    
    choice = input("\nEnter your choice (1/2/3): ").strip()
    
    if choice == "1":
        print("\n🌐 Starting Web Application...")
        print("📍 URL: http://localhost:5000")
        start_flask_server()
    elif choice == "2":
        print("\n📊 Starting Streamlit Dashboard...")
        print("📍 URL: http://localhost:8501")
        start_streamlit_app()
        input("Press Enter to stop the application...")
    elif choice == "3":
        print("\n🧪 Testing API connection...")
        try:
            import test_alpaca_connection_hardcoded
            print("✅ Connection test completed")
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
    else:
        print("❌ Invalid choice")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")