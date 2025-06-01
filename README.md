# Discord WoW Class Management Bot

A Discord bot that helps manage World of Warcraft class and specialization selections for your community members. The bot uses slash commands, integrates with Google Sheets for data storage, and includes role-based permissions.

## Features

- **Class Selection**: Choose from all 13 WoW classes with their respective specializations
- **Character Names**: Collect in-game character names for easy identification
- **One Character Per User**: Each Discord user can register one character (but can update it anytime)
- **Role Statistics**: Automatic role distribution tracking (Tank/Healer/Melee DPS/Ranged DPS)
- **Self-Management**: Players can update or delete their own selections
- **Admin Controls**: Admins can remove any player's selection
- **Role-Based Access**: Separate permissions for regular users and admins
- **Channel Restriction**: Bot only responds in designated channels
- **Google Sheets Integration**: Dual worksheet system with hidden sensitive columns
- **User-Friendly Interface**: Interactive dropdown menus, modals, and confirmation buttons
- **Change Tracking**: Logs when users update their selections with timestamps
- **Ephemeral Responses**: Private responses to keep channels clean
- **Auto-Updates**: Role statistics refresh automatically when selections change

## Supported Classes & Specializations

- **Death Knight**: Blood, Frost, Unholy
- **Demon Hunter**: Vengeance, Havoc
- **Druid**: Guardian, Restoration, Balance, Feral
- **Evoker**: Devastation, Preservation, Augmentation
- **Hunter**: Beast Mastery, Marksmanship, Survival
- **Mage**: Fire, Frost, Arcane
- **Monk**: Brewmaster, Windwalker, Mistweaver
- **Paladin**: Holy, Retribution, Protection
- **Priest**: Holy, Discipline, Shadow
- **Rogue**: Outlaw, Subtlety, Assassination
- **Shaman**: Elemental, Enhancement, Restoration
- **Warlock**: Affliction, Demonology, Destruction
- **Warrior**: Arms, Fury, Protection

## Commands

### **Player Commands**
- `/setclass` - Set or update your WoW class, specialization, and in-game character name
- `/myclass` - View your current character selection
- `/deleteclass` - Delete your character selection
- `/classlist` - View all available classes and specializations
- `/rolestats` - View role distribution statistics
- `/refreshstats` - Manually refresh role statistics

### **Admin Commands**
- `/removeuser <user>` - Remove a specific user's class selection (requires admin role)

## Prerequisites

1. **Python 3.8+**
2. **Discord Bot Token**
3. **Google Service Account** with Sheets API access
4. **Discord Server** with appropriate permissions

## Setup Instructions

### 1. Discord Bot Setup

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and bot
3. Copy the bot token
4. Enable the following bot permissions:
   - Send Messages
   - Use Slash Commands
   - Read Message History
   - View Channels
5. Invite the bot to your server with these permissions

### 2. Google Sheets Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API and Google Drive API
4. Create a service account:
   - Go to "Credentials" → "Create Credentials" → "Service Account"
   - Download the JSON key file
   - Rename it to `credentials.json` and place it in the bot directory
5. Share your Google Spreadsheet with the service account email (found in the JSON file)

### 3. Bot Installation

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

4. Fill in your configuration in `.env`:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   GUILD_ID=your_guild_id_here
   CHANNEL_ID=your_channel_id_here
   REQUIRED_ROLE=Member
   GOOGLE_CREDENTIALS_FILE=credentials.json
   SPREADSHEET_NAME=WoW Class Management
   ```

### 4. Configuration Details

#### Environment Variables

- **DISCORD_TOKEN**: Your Discord bot token (required)
- **GUILD_ID**: Your Discord server ID (optional, for faster command sync)
- **CHANNEL_ID**: Channel ID where the bot should work (optional, removes restriction if not set)
- **REQUIRED_ROLE**: Role name required to use the bot (optional, removes restriction if not set)
- **ADMIN_ROLE**: Role name required for admin commands (default: "Admin")
- **GOOGLE_CREDENTIALS_FILE**: Path to your Google service account JSON file
- **SPREADSHEET_NAME**: Name of the Google Spreadsheet to use
- **HIDDEN_COLUMNS**: Comma-separated list of column numbers to hide (default: "1,8,9")

#### Getting Discord IDs

1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click on your server → "Copy Server ID" (for GUILD_ID)
3. Right-click on the desired channel → "Copy Channel ID" (for CHANNEL_ID)

### 5. Running the Bot

```bash
python main.py
```

The bot will:
1. Connect to Discord
2. Set up Google Sheets connection
3. Sync slash commands
4. Start listening for interactions

## Google Sheets Structure

The bot automatically creates two worksheets:

### **Class Management Worksheet**
| Column | Description |
|--------|-------------|
| Discord ID | User's Discord ID (hidden by default) |
| Username | Discord username |
| Display Name | Server display name |
| In-Game Name | Player's WoW character name |
| Class | Selected WoW class |
| Specialization | Selected specialization |
| Last Updated | Timestamp of last update |
| Update Count | Number of times updated (hidden by default) |
| Notes | Additional information (hidden by default) |

### **Role Summary Worksheet**
| Column | Description |
|--------|-------------|
| Role | Tank, Healer, Melee DPS, Ranged DPS |
| Count | Number of players in each role |
| Percentage | Percentage of total players |
| Most Popular Class | Most chosen class for that role |
| Most Popular Spec | Most chosen specialization |
| Last Updated | Timestamp of last calculation |

## Usage

### **Setting Up Your Character**
1. Use `/setclass` in the designated channel
2. Choose your WoW class from the dropdown
3. Enter your in-game character name when prompted
4. Select your specialization
5. Your selection is automatically saved to Google Sheets

**Note:** Each Discord user can have **one character**. Using `/setclass` when you already have a character will update your existing selection.

### **Managing Your Character**
- **View**: Use `/myclass` to see your current character
- **Update**: Use `/setclass` to change your class, spec, or character name
- **Delete**: Use `/deleteclass` to remove your character entirely

### **Viewing Statistics**
- **Role Stats**: Use `/rolestats` to see role distribution
- **Class List**: Use `/classlist` to see all available options
- **Refresh**: Use `/refreshstats` to manually update statistics

### **Admin Features**
- **Remove User**: Use `/removeuser @username` to remove a player's selection
- **View Sheets**: Access Google Sheets for detailed management

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check that the bot has proper permissions and is in the correct channel
2. **Google Sheets errors**: Verify service account permissions and API access
3. **Command not found**: Ensure slash commands are synced (may take up to 1 hour globally)
4. **Permission denied**: Check that users have the required role

### Logs

The bot logs important events including:
- Successful connections
- Google Sheets operations
- User selections
- Errors and warnings

Check the console output for detailed information about any issues.

## Security Notes

- Never share your Discord bot token or Google credentials
- Keep the `credentials.json` file secure and out of version control
- Use environment variables for sensitive configuration
- Regularly rotate your bot token if compromised

## Support

If you encounter issues:

1. Check the logs for error messages
2. Verify all configuration values
3. Ensure proper permissions are set
4. Test with a simple setup first

## License

This project is provided as-is for community use. Modify as needed for your specific requirements.