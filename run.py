#!/usr/bin/env python3
"""
Discord WoW Class Management Bot Runner
This script performs setup checks and runs the bot.
"""

import sys
import os
import subprocess
from pathlib import Path

def check_setup():
    """Quick setup check before running"""
    issues = []
    
    # Check if .env exists
    if not Path('.env').exists():
        issues.append("Missing .env file (copy from .env.example)")
    
    # Check critical environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv('DISCORD_TOKEN'):
        issues.append("DISCORD_TOKEN not set in .env")
    
    creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    if not Path(creds_file).exists():
        issues.append(f"Google credentials file missing: {creds_file}")
    
    return issues

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def main():
    """Main runner function"""
    print("🚀 Starting Discord WoW Class Management Bot")
    print("=" * 45)
    
    # Quick setup check
    issues = check_setup()
    
    if issues:
        print("❌ Setup issues found:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n💡 Run 'python setup_check.py' for detailed setup verification")
        print("📖 See README.md for complete setup instructions")
        sys.exit(1)
    
    # Try to import required modules
    try:
        import discord
        import gspread
    except ImportError:
        print("📦 Some dependencies are missing. Installing...")
        if not install_dependencies():
            sys.exit(1)
    
    print("✅ Setup looks good!")
    print("🤖 Starting bot...\n")
    
    # Import and run the bot
    try:
        from main import bot
        bot.run(os.getenv('DISCORD_TOKEN'))
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()