#!/usr/bin/env python3
"""
Setup verification script for Discord WoW Class Management Bot
This script checks if all requirements are properly configured.
"""

import os
import sys
import json
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists and is readable"""
    if os.path.exists(file_path):
        print(f"✅ {description}: Found")
        return True
    else:
        print(f"❌ {description}: Missing ({file_path})")
        return False

def check_env_var(var_name, required=True):
    """Check if environment variable is set"""
    value = os.getenv(var_name)
    if value:
        print(f"✅ {var_name}: Set")
        return True
    elif required:
        print(f"❌ {var_name}: Missing (required)")
        return False
    else:
        print(f"⚠️  {var_name}: Not set (optional)")
        return True

def validate_google_credentials():
    """Validate Google credentials file"""
    creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    
    if not os.path.exists(creds_file):
        print(f"❌ Google credentials file not found: {creds_file}")
        return False
    
    try:
        with open(creds_file, 'r') as f:
            creds = json.load(f)
        
        required_fields = ['type', 'client_email', 'private_key', 'project_id']
        missing_fields = [field for field in required_fields if field not in creds]
        
        if missing_fields:
            print(f"❌ Google credentials missing fields: {', '.join(missing_fields)}")
            return False
        
        if creds.get('type') != 'service_account':
            print(f"❌ Google credentials must be for a service account")
            return False
        
        print(f"✅ Google credentials: Valid")
        print(f"   Service account: {creds['client_email']}")
        return True
        
    except json.JSONDecodeError:
        print(f"❌ Google credentials file is not valid JSON")
        return False
    except Exception as e:
        print(f"❌ Error reading Google credentials: {e}")
        return False

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python version: {version.major}.{version.minor}.{version.micro} (requires 3.8+)")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'discord',
        'gspread', 
        'oauth2client',
        'python-dotenv',
        'aiohttp'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}: Installed")
        except ImportError:
            print(f"❌ {package}: Missing")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def main():
    """Main setup check function"""
    print("🔍 Discord WoW Class Management Bot - Setup Check")
    print("=" * 50)
    
    # Load .env file if it exists
    env_file = Path('.env')
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ .env file loaded")
    else:
        print("⚠️  .env file not found (using system environment variables)")
    
    print("\n📋 Checking Requirements...")
    
    checks = []
    
    # Check Python version
    checks.append(check_python_version())
    
    # Check dependencies
    print("\n📦 Checking Dependencies...")
    checks.append(check_dependencies())
    
    # Check required files
    print("\n📁 Checking Files...")
    checks.append(check_file_exists('main.py', 'Main bot file'))
    checks.append(check_file_exists('requirements.txt', 'Requirements file'))
    
    # Check environment variables
    print("\n🔧 Checking Environment Variables...")
    checks.append(check_env_var('DISCORD_TOKEN', required=True))
    checks.append(check_env_var('GUILD_ID', required=False))
    checks.append(check_env_var('CHANNEL_ID', required=False))
    checks.append(check_env_var('REQUIRED_ROLE', required=False))
    checks.append(check_env_var('GOOGLE_CREDENTIALS_FILE', required=False))
    checks.append(check_env_var('SPREADSHEET_NAME', required=False))
    
    # Check Google credentials
    print("\n🔑 Checking Google Credentials...")
    checks.append(validate_google_credentials())
    
    # Summary
    print("\n" + "=" * 50)
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"🎉 Setup Check Complete: {passed}/{total} checks passed!")
        print("✅ Your bot is ready to run!")
        print("\nTo start the bot, run: python main.py")
    else:
        print(f"⚠️  Setup Check Complete: {passed}/{total} checks passed")
        print("❌ Please fix the issues above before running the bot.")
        
        print("\n🛠️  Quick fixes:")
        if not os.getenv('DISCORD_TOKEN'):
            print("- Set DISCORD_TOKEN in your .env file")
        if not os.path.exists(os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')):
            print("- Add your Google service account credentials file")
        print("- Run 'pip install -r requirements.txt' to install dependencies")
        
        sys.exit(1)

if __name__ == "__main__":
    main()