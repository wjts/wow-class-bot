# Discord WoW Class Management Bot - Deployment Guide

This guide covers multiple deployment options for your Discord bot on Proxmox or other environments.

## 🏗️ **Deployment Options Overview**

### **Recommended for Proxmox:**
1. **Docker Container** (Most Recommended)
2. **LXC Container** 
3. **VM with Systemd Service**

### **Other Options:**
4. **VPS/Cloud Deployment**
5. **Local Development**

---

## 🐳 **Option 1: Docker Deployment (Recommended)**

### **Advantages:**
- ✅ Easy to manage and update
- ✅ Isolated environment
- ✅ Automatic restarts
- ✅ Easy backups
- ✅ Works on any Docker-capable system

### **Setup Steps:**

#### **1. Prepare Proxmox CT Container**
```bash
# Create new CT container (Ubuntu 22.04/Debian 11)
# Allocate: 1 CPU, 1GB RAM, 8GB storage
# Enable: Nesting for Docker support

# In Proxmox CT container:
apt update && apt upgrade -y
apt install -y docker.io docker-compose git
systemctl enable docker
systemctl start docker
```

#### **2. Deploy the Bot**
```bash
# Clone your bot (or upload files)
cd /opt
git clone <your-repo> discord-bot
cd discord-bot

# Set up environment
cp .env.example .env
nano .env
# Fill in your configuration

# Copy Google credentials
# Upload credentials.json to this directory

# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f
```

#### **3. Management Commands**
```bash
# View status
docker-compose ps

# View logs
docker-compose logs -f discord-bot

# Restart bot
docker-compose restart

# Update bot
git pull
docker-compose build
docker-compose up -d

# Stop bot
docker-compose down
```

---

## 📦 **Option 2: LXC Container (Proxmox Native)**

### **Advantages:**
- ✅ Lower overhead than VM
- ✅ Direct Proxmox integration
- ✅ Easy snapshots/backups
- ✅ Resource efficient

### **Setup Steps:**

#### **1. Create LXC Container**
```bash
# In Proxmox web interface:
# - Create CT: Ubuntu 22.04 template
# - Resources: 1 CPU, 1GB RAM, 8GB storage
# - Network: DHCP or static IP
# - Options: Enable "Start at boot"
```

#### **2. Container Setup**
```bash
# Connect to container console
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git nano htop

# Create bot user
useradd -m -s /bin/bash botuser
sudo -u botuser mkdir -p /home/botuser/discord-bot
```

#### **3. Install Bot**
```bash
# Switch to bot user
sudo -u botuser -i

# Clone/upload bot files
cd ~/discord-bot
# Upload your bot files here

# Set up Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env
# Upload credentials.json

# Test run
python main.py
```

#### **4. Set up Systemd Service**
```bash
# As root, copy service file
cp /home/botuser/discord-bot/wow-class-bot.service /etc/systemd/system/

# Edit paths in service file
nano /etc/systemd/system/wow-class-bot.service
# Update paths to /home/botuser/discord-bot

# Enable and start
systemctl daemon-reload
systemctl enable wow-class-bot
systemctl start wow-class-bot

# Check status
systemctl status wow-class-bot
journalctl -u wow-class-bot -f
```

---

## 🖥️ **Option 3: VM with Systemd**

### **Setup Steps:**

#### **1. Create VM**
```bash
# In Proxmox:
# - Create VM: Ubuntu 22.04 Server
# - Resources: 1-2 CPU, 2GB RAM, 20GB storage
# - Enable: Start at boot
```

#### **2. System Setup**
```bash
# SSH into VM
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git ufw

# Configure firewall (optional)
ufw allow ssh
ufw enable

# Create directories
mkdir -p /opt/discord-bot
cd /opt/discord-bot
```

#### **3. Bot Installation**
```bash
# Upload/clone bot files
git clone <your-repo> .

# Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env
# Upload credentials.json

# Create bot user
useradd -r -s /bin/false -d /opt/discord-bot botuser
chown -R botuser:botuser /opt/discord-bot
```

#### **4. Systemd Service**
```bash
# Install service
cp wow-class-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable wow-class-bot
systemctl start wow-class-bot

# Monitor
systemctl status wow-class-bot
journalctl -u wow-class-bot -f
```

---

## ☁️ **Option 4: VPS/Cloud Deployment**

### **Popular Providers:**
- **DigitalOcean** ($5/month droplet)
- **Linode** ($5/month nanode)
- **Vultr** ($3.50/month instance)
- **AWS EC2** (t3.micro - free tier eligible)
- **Google Cloud** (e2-micro - free tier)

### **Quick Setup:**
```bash
# Create small VPS (1GB RAM minimum)
# Use Ubuntu 22.04 LTS

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Deploy bot
mkdir /opt/discord-bot
cd /opt/discord-bot
# Upload your files
docker-compose up -d
```

---

## 🔧 **Management & Monitoring**

### **Docker Management:**
```bash
# View logs
docker-compose logs -f

# Check resource usage
docker stats

# Backup
docker-compose down
tar czf bot-backup-$(date +%Y%m%d).tar.gz .

# Update
git pull
docker-compose build --no-cache
docker-compose up -d
```

### **Systemd Management:**
```bash
# Check status
systemctl status wow-class-bot

# View logs
journalctl -u wow-class-bot -f
journalctl -u wow-class-bot --since "1 hour ago"

# Restart
systemctl restart wow-class-bot

# Stop/Start
systemctl stop wow-class-bot
systemctl start wow-class-bot
```

### **Monitoring Script:**
```bash
#!/bin/bash
# monitor-bot.sh
while true; do
    if ! systemctl is-active --quiet wow-class-bot; then
        echo "Bot is down, restarting..."
        systemctl restart wow-class-bot
        # Optional: send notification
    fi
    sleep 60
done
```

---

## 🔒 **Security Best Practices**

### **General Security:**
```bash
# Update system regularly
apt update && apt upgrade -y

# Configure firewall
ufw allow ssh
ufw allow 22/tcp
ufw enable

# Disable root login (if using SSH)
nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
systemctl restart ssh
```

### **Bot Security:**
- ✅ Never commit `.env` or `credentials.json` to git
- ✅ Use non-root user for bot process
- ✅ Restrict file permissions (600 for sensitive files)
- ✅ Regular backups of configuration
- ✅ Monitor logs for errors

### **File Permissions:**
```bash
chmod 600 .env credentials.json
chmod 755 main.py
chown -R botuser:botuser /opt/discord-bot
```

---

## 📊 **Backup Strategy**

### **Automated Backup Script:**
```bash
#!/bin/bash
# backup-bot.sh
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup bot files
tar czf $BACKUP_DIR/discord-bot-$DATE.tar.gz \
    -C /opt/discord-bot \
    --exclude=venv \
    --exclude=__pycache__ \
    --exclude=logs \
    .

# Keep only last 7 backups
find $BACKUP_DIR -name "discord-bot-*.tar.gz" -mtime +7 -delete

echo "Backup completed: discord-bot-$DATE.tar.gz"
```

### **Crontab for Daily Backups:**
```bash
# Add to crontab (crontab -e)
0 2 * * * /opt/scripts/backup-bot.sh
```

---

## 🚀 **Performance Optimization**

### **Resource Requirements:**
- **Minimum:** 512MB RAM, 1 CPU
- **Recommended:** 1GB RAM, 1 CPU
- **Storage:** 5GB for bot + logs
- **Network:** Minimal bandwidth

### **Optimization Tips:**
```bash
# Limit log file sizes
# In systemd service or docker-compose

# Python optimizations
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# System optimizations
echo 'vm.swappiness=10' >> /etc/sysctl.conf
```

---

## 🔍 **Troubleshooting**

### **Common Issues:**

#### **Bot Won't Start:**
```bash
# Check logs
journalctl -u wow-class-bot -n 50

# Check environment
sudo -u botuser cat /opt/discord-bot/.env

# Test manually
sudo -u botuser -i
cd /opt/discord-bot
source venv/bin/activate
python main.py
```

#### **Google Sheets Errors:**
```bash
# Check credentials file
ls -la credentials.json
cat credentials.json | jq .

# Test API access
python3 -c "import gspread; print('Gspread working')"
```

#### **Discord Connection Issues:**
```bash
# Check token
echo $DISCORD_TOKEN

# Test network
ping discord.com
curl -I https://discord.com/api/v10/gateway
```

### **Health Check Script:**
```bash
#!/bin/bash
# health-check.sh
if systemctl is-active --quiet wow-class-bot; then
    echo "✅ Bot is running"
    exit 0
else
    echo "❌ Bot is not running"
    systemctl status wow-class-bot --no-pager
    exit 1
fi
```

---

## 📈 **Scaling & Updates**

### **Zero-Downtime Updates:**
```bash
# For Docker
docker-compose pull
docker-compose up -d

# For Systemd
git pull
systemctl restart wow-class-bot
```

### **Horizontal Scaling:**
- Bot is stateless (except Google Sheets)
- Can run multiple instances if needed
- Use load balancer for high availability

### **Database Migration:**
- Google Sheets handles scaling automatically
- Consider moving to proper database for high volume
- Backup before major updates

---

## 🎯 **Recommended Setup for Proxmox**

### **Best Choice: LXC + Docker**
```bash
# Create privileged LXC container
# - Template: Ubuntu 22.04
# - CPU: 1 core
# - RAM: 1GB
# - Storage: 8GB
# - Features: Enable nesting

# Inside container:
apt update && apt install -y docker.io docker-compose
cd /opt && git clone <repo> discord-bot
cd discord-bot
cp .env.example .env && nano .env
docker-compose up -d
```

This gives you:
- ✅ Low overhead
- ✅ Easy management
- ✅ Container isolation
- ✅ Proxmox integration
- ✅ Simple backups/snapshots

Your bot will be running reliably 24/7! 🎉