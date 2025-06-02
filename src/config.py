import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID')) if os.getenv('GUILD_ID') else None
CHANNEL_ID = int(os.getenv('CHANNEL_ID')) if os.getenv('CHANNEL_ID') else None
REQUIRED_ROLE = os.getenv('REQUIRED_ROLE', 'Member')
ADMIN_ROLE = os.getenv('ADMIN_ROLE', 'Admin')

# Google Sheets configuration
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME', 'WoW Class Management')

# Class and specialization data
CLASS_SPECS = {
    "Death Knight": ["Blood", "Frost", "Unholy"],
    "Demon Hunter": ["Vengeance", "Havoc"],
    "Druid": ["Guardian", "Restoration", "Balance", "Feral"],
    "Evoker": ["Devastation", "Preservation", "Augmentation"],
    "Hunter": ["Beast Mastery", "Marksmanship", "Survival"],
    "Mage": ["Fire", "Frost", "Arcane"],
    "Monk": ["Brewmaster", "Windwalker", "Mistweaver"],
    "Paladin": ["Holy", "Retribution", "Protection"],
    "Priest": ["Holy", "Discipline", "Shadow"],
    "Rogue": ["Outlaw", "Subtlety", "Assassination"],
    "Shaman": ["Elemental", "Enhancement", "Restoration"],
    "Warlock": ["Affliction", "Demonology", "Destruction"],
    "Warrior": ["Arms", "Fury", "Protection"]
}