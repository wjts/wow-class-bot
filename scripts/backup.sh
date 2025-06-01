#!/bin/bash
set -e

# Discord WoW Class Management Bot - Backup Script
# Automated backup of bot configuration and data

# Configuration
BOT_DIR="/opt/discord-bot"
BACKUP_DIR="/opt/backups/discord-bot"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="discord-bot-backup-$DATE"
KEEP_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Discord Bot Backup Script${NC}"
echo "================================"

# Check if bot directory exists
if [ ! -d "$BOT_DIR" ]; then
    echo -e "${RED}❌ Bot directory not found: $BOT_DIR${NC}"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo -e "${YELLOW}📁 Creating backup directory...${NC}"
FULL_BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
mkdir -p "$FULL_BACKUP_PATH"

# Function to backup files
backup_files() {
    echo -e "${YELLOW}📋 Backing up bot files...${NC}"
    
    # Copy essential files
    cp "$BOT_DIR/main.py" "$FULL_BACKUP_PATH/" 2>/dev/null || echo "⚠️  main.py not found"
    cp "$BOT_DIR/requirements.txt" "$FULL_BACKUP_PATH/" 2>/dev/null || echo "⚠️  requirements.txt not found"
    cp "$BOT_DIR/.env" "$FULL_BACKUP_PATH/" 2>/dev/null || echo "⚠️  .env not found"
    cp "$BOT_DIR/credentials.json" "$FULL_BACKUP_PATH/" 2>/dev/null || echo "⚠️  credentials.json not found"
    cp "$BOT_DIR/README.md" "$FULL_BACKUP_PATH/" 2>/dev/null || echo "⚠️  README.md not found"
    cp "$BOT_DIR/setup_check.py" "$FULL_BACKUP_PATH/" 2>/dev/null || echo "⚠️  setup_check.py not found"
    cp "$BOT_DIR/run.py" "$FULL_BACKUP_PATH/" 2>/dev/null || echo "⚠️  run.py not found"
    
    # Copy Docker files if they exist
    cp "$BOT_DIR/Dockerfile" "$FULL_BACKUP_PATH/" 2>/dev/null || true
    cp "$BOT_DIR/docker-compose.yml" "$FULL_BACKUP_PATH/" 2>/dev/null || true
    
    # Copy systemd service file if it exists
    cp "/etc/systemd/system/wow-class-bot.service" "$FULL_BACKUP_PATH/" 2>/dev/null || true
    
    # Copy logs directory if it exists
    if [ -d "$BOT_DIR/logs" ]; then
        cp -r "$BOT_DIR/logs" "$FULL_BACKUP_PATH/" || echo "⚠️  Could not backup logs"
    fi
}

# Function to create metadata
create_metadata() {
    echo -e "${YELLOW}📝 Creating backup metadata...${NC}"
    
    cat > "$FULL_BACKUP_PATH/backup_info.txt" << EOF
Discord WoW Class Management Bot - Backup Information
====================================================

Backup Date: $(date)
Backup Name: $BACKUP_NAME
Bot Directory: $BOT_DIR
Hostname: $(hostname)
System: $(uname -a)

Files Included:
$(ls -la "$FULL_BACKUP_PATH" 2>/dev/null || echo "Error listing files")

Bot Status at Backup Time:
$(systemctl status wow-class-bot --no-pager 2>/dev/null || echo "Systemd service not found")

Disk Usage:
$(du -sh "$BOT_DIR" 2>/dev/null || echo "Could not calculate disk usage")

Python Version:
$(python3 --version 2>/dev/null || echo "Python not found")

Environment Variables (sanitized):
$(grep -v "TOKEN\|SECRET\|PASSWORD\|KEY" "$BOT_DIR/.env" 2>/dev/null || echo ".env file not accessible")

Git Information (if applicable):
$(cd "$BOT_DIR" && git log --oneline -5 2>/dev/null || echo "Not a git repository")
EOF
}

# Function to compress backup
compress_backup() {
    echo -e "${YELLOW}🗜️  Compressing backup...${NC}"
    
    cd "$BACKUP_DIR"
    tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
    
    if [ $? -eq 0 ]; then
        rm -rf "$BACKUP_NAME"
        echo -e "${GREEN}✅ Backup compressed: $BACKUP_NAME.tar.gz${NC}"
        
        # Show backup size
        BACKUP_SIZE=$(du -h "$BACKUP_NAME.tar.gz" | cut -f1)
        echo -e "${BLUE}📊 Backup size: $BACKUP_SIZE${NC}"
    else
        echo -e "${RED}❌ Failed to compress backup${NC}"
        exit 1
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    echo -e "${YELLOW}🧹 Cleaning up old backups...${NC}"
    
    # Remove backups older than KEEP_DAYS
    find "$BACKUP_DIR" -name "discord-bot-backup-*.tar.gz" -mtime +$KEEP_DAYS -delete 2>/dev/null || true
    
    # Count remaining backups
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/discord-bot-backup-*.tar.gz 2>/dev/null | wc -l)
    echo -e "${BLUE}📦 Total backups: $BACKUP_COUNT${NC}"
}

# Function to verify backup
verify_backup() {
    echo -e "${YELLOW}🔍 Verifying backup...${NC}"
    
    if [ -f "$BACKUP_DIR/$BACKUP_NAME.tar.gz" ]; then
        # Test if archive is valid
        tar -tzf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Backup verification successful${NC}"
        else
            echo -e "${RED}❌ Backup verification failed${NC}"
            exit 1
        fi
    else
        echo -e "${RED}❌ Backup file not found${NC}"
        exit 1
    fi
}

# Function to send notification (optional)
send_notification() {
    # You can customize this to send notifications via webhook, email, etc.
    echo -e "${BLUE}📬 Backup completed successfully${NC}"
    echo -e "${BLUE}📍 Location: $BACKUP_DIR/$BACKUP_NAME.tar.gz${NC}"
    
    # Example webhook notification (uncomment and configure if needed)
    # curl -X POST -H 'Content-type: application/json' \
    #     --data '{"text":"Discord bot backup completed: '$BACKUP_NAME'"}' \
    #     YOUR_WEBHOOK_URL
}

# Main backup process
main() {
    echo -e "${BLUE}🚀 Starting backup process...${NC}"
    
    # Check if running as root (not recommended)
    if [ "$EUID" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  Running as root. Consider using a dedicated backup user.${NC}"
    fi
    
    # Stop bot for consistent backup (optional)
    read -t 10 -p "Stop bot during backup for consistency? (y/N): " -n 1 -r || REPLY='N'
    echo
    
    BOT_WAS_RUNNING=false
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if systemctl is-active --quiet wow-class-bot; then
            BOT_WAS_RUNNING=true
            echo -e "${YELLOW}⏸️  Stopping bot...${NC}"
            systemctl stop wow-class-bot
        fi
    fi
    
    # Perform backup
    backup_files
    create_metadata
    compress_backup
    verify_backup
    cleanup_old_backups
    
    # Restart bot if it was running
    if [ "$BOT_WAS_RUNNING" = true ]; then
        echo -e "${YELLOW}▶️  Restarting bot...${NC}"
        systemctl start wow-class-bot
        sleep 3
        if systemctl is-active --quiet wow-class-bot; then
            echo -e "${GREEN}✅ Bot restarted successfully${NC}"
        else
            echo -e "${RED}❌ Failed to restart bot${NC}"
        fi
    fi
    
    send_notification
    
    echo ""
    echo -e "${GREEN}🎉 Backup completed successfully!${NC}"
    echo -e "${BLUE}📁 Backup location: $BACKUP_DIR/$BACKUP_NAME.tar.gz${NC}"
    echo ""
    echo -e "${YELLOW}📋 To restore from this backup:${NC}"
    echo -e "${YELLOW}   1. Extract: tar -xzf $BACKUP_NAME.tar.gz${NC}"
    echo -e "${YELLOW}   2. Copy files to bot directory${NC}"
    echo -e "${YELLOW}   3. Restart bot service${NC}"
}

# Handle script interruption
trap 'echo -e "\n${RED}❌ Backup interrupted${NC}"; exit 1' INT TERM

# Run main function
main "$@"