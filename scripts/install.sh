#!/bin/bash
set -e

# Discord WoW Class Management Bot - Installation Script
# This script automates the deployment process

echo "🚀 Discord WoW Class Management Bot - Installation"
echo "=================================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please do not run this script as root"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    echo "❌ Cannot detect OS"
    exit 1
fi

echo "📋 Detected OS: $OS $VER"

# Function to install dependencies
install_dependencies() {
    echo "📦 Installing system dependencies..."
    
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv git curl wget nano
    elif [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Red Hat"* ]]; then
        sudo yum install -y python3 python3-pip git curl wget nano
    else
        echo "⚠️  OS not fully supported, attempting generic install..."
        sudo apt update && sudo apt install -y python3 python3-pip python3-venv git curl wget nano || \
        sudo yum install -y python3 python3-pip git curl wget nano
    fi
}

# Function to setup bot directory
setup_bot_directory() {
    echo "📁 Setting up bot directory..."
    
    BOT_DIR="/opt/discord-bot"
    
    if [ -d "$BOT_DIR" ]; then
        echo "⚠️  Directory $BOT_DIR already exists"
        read -p "Do you want to backup and overwrite? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo mv "$BOT_DIR" "$BOT_DIR.backup.$(date +%Y%m%d_%H%M%S)"
            echo "✅ Backed up existing directory"
        else
            echo "❌ Installation cancelled"
            exit 1
        fi
    fi
    
    sudo mkdir -p "$BOT_DIR"
    sudo chown $(whoami):$(whoami) "$BOT_DIR"
}

# Function to setup Python environment
setup_python_env() {
    echo "🐍 Setting up Python environment..."
    
    cd "$BOT_DIR"
    
    # Copy current directory files or clone from git
    if [ -f "../main.py" ]; then
        echo "📋 Copying bot files..."
        cp -r ../. .
    else
        echo "❌ Bot files not found. Please run this script from the bot directory"
        exit 1
    fi
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Install requirements
    pip install -r requirements.txt
    
    echo "✅ Python environment ready"
}

# Function to configure environment
configure_environment() {
    echo "⚙️  Configuring environment..."
    
    cd "$BOT_DIR"
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        echo "📝 Created .env file from template"
        echo ""
        echo "🔧 Please edit .env file with your configuration:"
        echo "   nano .env"
        echo ""
        echo "Required settings:"
        echo "   - DISCORD_TOKEN=your_bot_token"
        echo "   - GUILD_ID=your_server_id"
        echo "   - CHANNEL_ID=your_channel_id"
        echo ""
        read -p "Press Enter when you've configured .env file..."
    fi
    
    if [ ! -f "credentials.json" ]; then
        echo ""
        echo "🔑 Google Service Account Setup Required:"
        echo "   1. Create a Google Cloud project"
        echo "   2. Enable Google Sheets API"
        echo "   3. Create a service account"
        echo "   4. Download the JSON key file"
        echo "   5. Save it as 'credentials.json' in this directory"
        echo ""
        read -p "Press Enter when you've added credentials.json..."
    fi
}

# Function to setup systemd service
setup_systemd_service() {
    echo "🔧 Setting up systemd service..."
    
    # Create bot user
    if ! id "botuser" &>/dev/null; then
        sudo useradd -r -s /bin/false -d "$BOT_DIR" botuser
        echo "👤 Created botuser"
    fi
    
    # Set permissions
    sudo chown -R botuser:botuser "$BOT_DIR"
    sudo chmod 600 "$BOT_DIR/.env" "$BOT_DIR/credentials.json" 2>/dev/null || true
    
    # Create systemd service
    sudo tee /etc/systemd/system/wow-class-bot.service > /dev/null <<EOF
[Unit]
Description=WoW Class Management Discord Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=botuser
Group=botuser
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=wow-class-bot

EnvironmentFile=$BOT_DIR/.env

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$BOT_DIR/logs

[Install]
WantedBy=multi-user.target
EOF
    
    # Enable and start service
    sudo systemctl daemon-reload
    sudo systemctl enable wow-class-bot
    
    echo "✅ Systemd service configured"
}

# Function to setup Docker (optional)
setup_docker_option() {
    echo ""
    read -p "🐳 Do you want to install Docker for container deployment? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 Installing Docker..."
        
        # Install Docker
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $(whoami)
        rm get-docker.sh
        
        # Install Docker Compose
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        
        echo "✅ Docker installed (you may need to log out and back in)"
        echo "🐳 To use Docker: docker-compose up -d"
    fi
}

# Function to test installation
test_installation() {
    echo "🧪 Testing installation..."
    
    cd "$BOT_DIR"
    
    # Test Python dependencies
    source venv/bin/activate
    python -c "import discord, gspread; print('✅ Dependencies OK')" || {
        echo "❌ Python dependencies test failed"
        exit 1
    }
    
    # Test configuration files
    if [ -f ".env" ] && [ -f "credentials.json" ]; then
        echo "✅ Configuration files present"
    else
        echo "⚠️  Configuration files missing"
    fi
    
    # Test systemd service
    if sudo systemctl is-enabled wow-class-bot &>/dev/null; then
        echo "✅ Systemd service enabled"
    else
        echo "⚠️  Systemd service not enabled"
    fi
}

# Function to show completion message
show_completion() {
    echo ""
    echo "🎉 Installation Complete!"
    echo "======================="
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Verify your .env configuration: nano $BOT_DIR/.env"
    echo "   2. Check Google credentials: ls -la $BOT_DIR/credentials.json"
    echo "   3. Start the bot: sudo systemctl start wow-class-bot"
    echo "   4. Check status: sudo systemctl status wow-class-bot"
    echo "   5. View logs: journalctl -u wow-class-bot -f"
    echo ""
    echo "🔧 Management Commands:"
    echo "   Start:   sudo systemctl start wow-class-bot"
    echo "   Stop:    sudo systemctl stop wow-class-bot"
    echo "   Restart: sudo systemctl restart wow-class-bot"
    echo "   Status:  sudo systemctl status wow-class-bot"
    echo "   Logs:    journalctl -u wow-class-bot -f"
    echo ""
    echo "📊 Health Check:"
    echo "   Run: python $BOT_DIR/setup_check.py"
    echo ""
    echo "🎮 Your Discord bot is ready to manage WoW classes!"
}

# Main installation flow
main() {
    echo "Starting installation process..."
    echo ""
    
    # Check if we're in the right directory
    if [ ! -f "main.py" ]; then
        echo "❌ Please run this script from the discord-bot directory"
        exit 1
    fi
    
    install_dependencies
    setup_bot_directory
    setup_python_env
    configure_environment
    setup_systemd_service
    setup_docker_option
    test_installation
    show_completion
}

# Run main function
main "$@"