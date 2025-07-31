#!/usr/bin/env python3
"""
Quick start script for the Trading Strategy Scanner
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    return True

def install_requirements():
    """Install required packages"""
    print("📦 Installing required packages...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Packages installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False

def check_files():
    """Check if required files exist"""
    required_files = [
        'server.py',
        'index.html',
        'styles.css',
        'app.js',
        'requirements.txt'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    return True

def start_server():
    """Start the Flask server"""
    print("🚀 Starting Trading Strategy Scanner...")
    print("=" * 50)
    
    try:
        # Start server in a subprocess
        process = subprocess.Popen([
            sys.executable, "server.py"
        ])
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Open browser
        print("🌐 Opening browser...")
        webbrowser.open("http://localhost:5000")
        
        # Wait for process
        process.wait()
        
    except KeyboardInterrupt:
        print("\n👋 Stopping server...")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print(f"❌ Error starting server: {e}")

def main():
    """Main function"""
    print("🚀 Trading Strategy Scanner - Quick Start")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return
    
    # Check required files
    if not check_files():
        return
    
    # Ask user if they want to install requirements
    install = input("📦 Install/update required packages? (y/n): ").lower().strip()
    if install in ['y', 'yes', '']:
        if not install_requirements():
            return
    
    print("\n🎯 Configuration:")
    print("   • API Keys: Configured in server.py")
    print("   • Data Feed: IEX (Free)")
    print("   • Paper Trading: Disabled")
    print("   • Port: 5000")
    
    start_input = input("\n🚀 Start the server? (y/n): ").lower().strip()
    if start_input in ['y', 'yes', '']:
        start_server()
    else:
        print("👋 Goodbye!")

if __name__ == '__main__':
    main()