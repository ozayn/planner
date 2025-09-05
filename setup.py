#!/usr/bin/env python3
"""
Setup script for Event Planner App
"""

import os
import sys
import subprocess
import shutil

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_dependencies():
    """Install Python dependencies"""
    return run_command("pip install -r requirements.txt", "Installing Python dependencies")

def setup_environment():
    """Setup environment file"""
    env_file = ".env"
    env_example = "env_example.txt"
    
    if not os.path.exists(env_file):
        if os.path.exists(env_example):
            shutil.copy(env_example, env_file)
            print(f"✅ Created {env_file} from {env_example}")
            print("📝 Please update .env with your actual configuration values")
        else:
            print("⚠️  No environment file found. Please create .env manually")
    else:
        print("✅ Environment file already exists")

def setup_database():
    """Initialize database with sample data"""
    return run_command("python3 scripts/seed_data.py", "Setting up database with sample data")

def create_directories():
    """Create necessary directories"""
    directories = ['templates', 'static', 'static/css', 'static/js', 'static/images']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Created directory: {directory}")
        else:
            print(f"✅ Directory already exists: {directory}")

def main():
    """Main setup function"""
    print("🚀 Setting up Event Planner App...")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    # Setup database
    if not setup_database():
        print("❌ Failed to setup database")
        sys.exit(1)
    
    print("=" * 50)
    print("🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Update .env file with your configuration")
    print("2. Run: python app.py")
    print("3. Open: http://localhost:3000")
    print("\n📚 For more information, see README.md")

if __name__ == "__main__":
    main()
