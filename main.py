import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import json
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID')) if os.getenv('GUILD_ID') else None
CHANNEL_ID = int(os.getenv('CHANNEL_ID')) if os.getenv('CHANNEL_ID') else None
REQUIRED_ROLE = os.getenv('REQUIRED_ROLE', 'Member')
ADMIN_ROLE = os.getenv('ADMIN_ROLE', 'Admin')
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
SPREADSHEET_NAME = os.getenv('SPREADSHEET_NAME', 'WoW Class Management')

# Columns to hide (1-based index): Discord ID, Update Count, Notes
HIDDEN_COLUMNS_STR = os.getenv('HIDDEN_COLUMNS', '1,8,9')
HIDDEN_COLUMNS = [int(x.strip()) for x in HIDDEN_COLUMNS_STR.split(',') if x.strip().isdigit()]

# Role classifications
ROLE_SPECS = {
    "Tank": [
        ("Death Knight", "Blood"),
        ("Demon Hunter", "Vengeance"),
        ("Druid", "Guardian"),
        ("Monk", "Brewmaster"),
        ("Paladin", "Protection"),
        ("Warrior", "Protection")
    ],
    "Healer": [
        ("Druid", "Restoration"),
        ("Evoker", "Preservation"),
        ("Monk", "Mistweaver"),
        ("Paladin", "Holy"),
        ("Priest", "Holy"),
        ("Priest", "Discipline"),
        ("Shaman", "Restoration")
    ],
    "Melee DPS": [
        ("Death Knight", "Frost"),
        ("Death Knight", "Unholy"),
        ("Demon Hunter", "Havoc"),
        ("Druid", "Feral"),
        ("Hunter", "Survival"),
        ("Monk", "Windwalker"),
        ("Paladin", "Retribution"),
        ("Rogue", "Outlaw"),
        ("Rogue", "Subtlety"),
        ("Rogue", "Assassination"),
        ("Shaman", "Enhancement"),
        ("Warrior", "Arms"),
        ("Warrior", "Fury")
    ],
    "Ranged DPS": [
        ("Druid", "Balance"),
        ("Evoker", "Devastation"),
        ("Evoker", "Augmentation"),
        ("Hunter", "Beast Mastery"),
        ("Hunter", "Marksmanship"),
        ("Mage", "Fire"),
        ("Mage", "Frost"),
        ("Mage", "Arcane"),
        ("Priest", "Shadow"),
        ("Warlock", "Affliction"),
        ("Warlock", "Demonology"),
        ("Warlock", "Destruction")
    ]
}

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

class ClassSpecBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.google_sheet = None
        self.worksheet = None
        self.summary_worksheet = None
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        await self.setup_google_sheets()
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild {GUILD_ID}")
        else:
            await self.tree.sync()
            logger.info("Synced commands globally")
    
    async def setup_google_sheets(self):
        """Set up Google Sheets connection"""
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
                logger.error(f"Google credentials file {GOOGLE_CREDENTIALS_FILE} not found!")
                return
            
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                GOOGLE_CREDENTIALS_FILE, scope
            )
            client = gspread.authorize(creds)
            
            # Try to open existing spreadsheet or create new one
            try:
                self.google_sheet = client.open(SPREADSHEET_NAME)
                logger.info(f"Opened existing spreadsheet: {SPREADSHEET_NAME}")
            except gspread.SpreadsheetNotFound:
                self.google_sheet = client.create(SPREADSHEET_NAME)
                logger.info(f"Created new spreadsheet: {SPREADSHEET_NAME}")
            
            # Get or create the main worksheet
            try:
                self.worksheet = self.google_sheet.worksheet("Class Management")
                # Hide columns for existing worksheet too
                await self.hide_columns()
            except gspread.WorksheetNotFound:
                self.worksheet = self.google_sheet.add_worksheet(
                    title="Class Management", rows="1000", cols="10"
                )
                # Set up headers
                headers = [
                    "Discord ID", "Username", "Display Name", "In-Game Name", "Class", 
                    "Specialization", "Last Updated", "Update Count", "Notes"
                ]
                self.worksheet.append_row(headers)
                
                # Hide specified columns
                await self.hide_columns()
                logger.info("Created new worksheet with headers and hidden columns")
            
            # Get or create the summary worksheet
            try:
                self.summary_worksheet = self.google_sheet.worksheet("Role Summary")
            except gspread.WorksheetNotFound:
                self.summary_worksheet = self.google_sheet.add_worksheet(
                    title="Role Summary", rows="100", cols="6"
                )
                # Set up summary headers
                summary_headers = [
                    "Role", "Count", "Percentage", "Most Popular Class", "Most Popular Spec", "Last Updated"
                ]
                self.summary_worksheet.append_row(summary_headers)
                logger.info("Created summary worksheet")
            
            # Update summary on startup
            await self.update_role_summary()
            
        except Exception as e:
            logger.error(f"Failed to setup Google Sheets: {e}")
    
    async def hide_columns(self):
        """Hide specified columns in the worksheet"""
        try:
            if not self.worksheet or not HIDDEN_COLUMNS:
                return
            
            # Get the spreadsheet ID and worksheet ID
            spreadsheet_id = self.google_sheet.id
            worksheet_id = self.worksheet.id
            
            # Create requests to hide columns
            requests = []
            for col_index in HIDDEN_COLUMNS:
                requests.append({
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': worksheet_id,
                            'dimension': 'COLUMNS',
                            'startIndex': col_index - 1,  # Convert to 0-based
                            'endIndex': col_index
                        },
                        'properties': {
                            'hiddenByUser': True
                        },
                        'fields': 'hiddenByUser'
                    }
                })
            
            if requests:
                # Execute the batch update
                body = {'requests': requests}
                self.google_sheet.batch_update(body)
                logger.info(f"Hidden columns: {HIDDEN_COLUMNS}")
                
        except Exception as e:
            logger.error(f"Failed to hide columns: {e}")
    
    def get_role_for_spec(self, class_name: str, spec: str) -> str:
        """Get the role for a given class and specialization"""
        for role, specs in ROLE_SPECS.items():
            if (class_name, spec) in specs:
                return role
        return "Unknown"
    
    async def update_role_summary(self):
        """Update the role summary worksheet with current statistics"""
        try:
            if not self.worksheet or not self.summary_worksheet:
                return
            
            # Get all current selections
            all_records = self.worksheet.get_all_records()
            
            # Count roles
            role_counts = {"Tank": 0, "Healer": 0, "Melee DPS": 0, "Ranged DPS": 0, "Unknown": 0}
            class_counts = {}
            spec_counts = {}
            role_classes = {role: {} for role in role_counts.keys()}
            role_specs = {role: {} for role in role_counts.keys()}
            
            for record in all_records:
                # Handle potential column misalignment by looking for actual data
                class_name = ''
                spec = ''
                
                # Try to find class and spec in the record, regardless of column names
                for key, value in record.items():
                    if value in [cls for cls in CLASS_SPECS.keys()]:
                        class_name = value
                    elif class_name and value in CLASS_SPECS.get(class_name, []):
                        spec = value
                
                if class_name and spec:
                    role = self.get_role_for_spec(class_name, spec)
                    role_counts[role] += 1
                    
                    # Track class popularity per role
                    if role not in role_classes:
                        role_classes[role] = {}
                    role_classes[role][class_name] = role_classes[role].get(class_name, 0) + 1
                    
                    # Track spec popularity per role
                    if role not in role_specs:
                        role_specs[role] = {}
                    spec_key = f"{class_name} {spec}"
                    role_specs[role][spec_key] = role_specs[role].get(spec_key, 0) + 1
            
            # Calculate totals and percentages
            total_players = sum(role_counts.values())
            
            # Clear existing summary data (keep headers)
            self.summary_worksheet.clear()
            summary_headers = [
                "Role", "Count", "Percentage", "Most Popular Class", "Most Popular Spec", "Last Updated"
            ]
            self.summary_worksheet.append_row(summary_headers)
            
            # Add role statistics
            current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            
            for role in ["Tank", "Healer", "Melee DPS", "Ranged DPS"]:
                count = role_counts[role]
                percentage = f"{(count / total_players * 100):.1f}%" if total_players > 0 else "0%"
                
                # Find most popular class and spec for this role
                most_popular_class = max(role_classes[role], key=role_classes[role].get) if role_classes[role] else "None"
                most_popular_spec = max(role_specs[role], key=role_specs[role].get) if role_specs[role] else "None"
                
                self.summary_worksheet.append_row([
                    role, count, percentage, most_popular_class, most_popular_spec, current_time
                ])
            
            # Add total row
            self.summary_worksheet.append_row([
                "TOTAL", total_players, "100%", "", "", current_time
            ])
            
            logger.info(f"Updated role summary: {total_players} total players")
            
        except Exception as e:
            logger.error(f"Failed to update role summary: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        if CHANNEL_ID:
            channel = self.get_channel(CHANNEL_ID)
            if channel:
                logger.info(f"Bot will listen on channel: {channel.name}")
            else:
                logger.warning(f"Could not find channel with ID: {CHANNEL_ID}")

bot = ClassSpecBot()

def has_required_role():
    """Check if user has the required role"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not REQUIRED_ROLE:
            return True
        
        user_roles = [role.name for role in interaction.user.roles]
        return REQUIRED_ROLE in user_roles
    
    return app_commands.check(predicate)

def has_admin_role():
    """Check if user has the admin role"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not ADMIN_ROLE:
            return True
        
        user_roles = [role.name for role in interaction.user.roles]
        return ADMIN_ROLE in user_roles
    
    return app_commands.check(predicate)

def is_correct_channel():
    """Check if command is used in the correct channel"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not CHANNEL_ID:
            return True
        return interaction.channel_id == CHANNEL_ID
    
    return app_commands.check(predicate)

class ClassSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=class_name, value=class_name)
            for class_name in sorted(CLASS_SPECS.keys())
        ]
        super().__init__(placeholder="Choose your class...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        selected_class = self.values[0]
        
        # Show modal to collect in-game name
        modal = NicknameModal(selected_class, interaction.user, interaction.message)
        await interaction.response.send_modal(modal)

class NicknameModal(discord.ui.Modal, title="Enter Your In-Game Name"):
    def __init__(self, class_name: str, user: discord.User, original_message):
        super().__init__()
        self.class_name = class_name
        self.user = user
        self.original_message = original_message
    
    nickname = discord.ui.TextInput(
        label="In-Game Character Name",
        placeholder="Enter your WoW character name...",
        max_length=50,
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        view = SpecSelectView(self.class_name, self.user, self.nickname.value, interaction)
        
        embed = discord.Embed(
            title="Select Specialization",
            description=f"You selected **{self.class_name}** for character **{self.nickname.value}**.\nNow choose your specialization:",
            color=0x00ff00
        )
        
        # Use the modal interaction to edit the original message
        await interaction.response.edit_message(embed=embed, view=view)

class ClassSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(ClassSelect())

class SpecSelect(discord.ui.Select):
    def __init__(self, class_name: str, nickname: str, modal_interaction):
        self.class_name = class_name
        self.nickname = nickname
        self.modal_interaction = modal_interaction
        options = [
            discord.SelectOption(label=spec, value=spec)
            for spec in CLASS_SPECS[class_name]
        ]
        super().__init__(placeholder="Choose your specialization...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        # Check if this is the correct user
        if interaction.user != self.modal_interaction.user:
            await interaction.response.send_message("You can't use this dropdown!", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        selected_spec = self.values[0]
        
        # Save to Google Sheets
        success = await save_to_sheets(
            self.modal_interaction.user.id,
            self.modal_interaction.user.name,
            self.modal_interaction.user.display_name,
            self.nickname,
            self.class_name,
            selected_spec
        )
        
        if success:
            embed = discord.Embed(
                title="✅ Selection Saved!",
                description=f"**Character:** {self.nickname}\n**Class:** {self.class_name} - {selected_spec}",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Your selection has been saved to the database.")
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="There was an error saving your selection. Please try again later.",
                color=0xff0000
            )
        
        await interaction.edit_original_response(embed=embed, view=None)

class SpecSelectView(discord.ui.View):
    def __init__(self, class_name: str, user: discord.User, nickname: str, modal_interaction):
        super().__init__(timeout=300)
        self.class_name = class_name
        self.user = user
        self.nickname = nickname
        self.modal_interaction = modal_interaction
        self.add_item(SpecSelect(class_name, nickname, modal_interaction))
    
    @discord.ui.button(label="🔙 Back to Classes", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.modal_interaction.user:
            await interaction.response.send_message("You can't use this button!", ephemeral=True)
            return
        
        view = ClassSelectView()
        embed = discord.Embed(
            title="Select Your Class",
            description="Choose your World of Warcraft class from the dropdown below:",
            color=0x0099ff
        )
        
        await interaction.response.edit_message(embed=embed, view=view)

async def save_to_sheets(user_id: int, username: str, display_name: str, nickname: str, class_name: str, spec: str) -> bool:
    """Save user selection to Google Sheets"""
    try:
        if not bot.worksheet:
            logger.error("Google Sheets not set up properly")
            return False
        
        # Get all records to check if user exists
        try:
            # Check if user already exists
            all_records = bot.worksheet.get_all_records()
            user_found = False
            row_num = 0
        
            # Look for existing user by Discord ID (regardless of column position)
            for idx, record in enumerate(all_records):
                # Check all possible columns where Discord ID might be stored
                discord_id_value = None
                for key, value in record.items():
                    if str(value) == str(user_id):
                        discord_id_value = value
                        break
            
                if discord_id_value:
                    user_found = True
                    row_num = idx + 2  # +2 because records start from row 2 (after header)
                    break
            
            current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            
            if user_found:
                # Update existing entry
                try:
                    current_count = int(all_records[idx].get('Update Count', 0))
                    update_count = current_count + 1
                except (ValueError, TypeError):
                    update_count = 1
                
                # Update the row using batch update
                row_data = [
                    [str(user_id), username, display_name, nickname, class_name, 
                     spec, current_time, update_count, "Updated selection"]
                ]
                bot.worksheet.update(f"A{row_num}:I{row_num}", row_data, value_input_option='USER_ENTERED')
                
                logger.info(f"Updated user {username} - {class_name}/{spec}")
            else:
                # Add new entry using batch update
                new_row = len(all_records) + 2  # +2 for header row
                row_data = [
                    [str(user_id), username, display_name, nickname, class_name, 
                     spec, current_time, 1, "Initial selection"]
                ]
                bot.worksheet.update(f"A{new_row}:I{new_row}", row_data, value_input_option='USER_ENTERED')
                
                logger.info(f"Added new user {username} - {class_name}/{spec}")
        
        except Exception as e:
            # Fallback: add new row using batch update
            try:
                current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                # Find the next available row
                all_values = bot.worksheet.get_all_values()
                new_row = len(all_values) + 1
                
                row_data = [
                    [str(user_id), username, display_name, nickname, class_name, 
                     spec, current_time, 1, "Selection (fallback)"]
                ]
                bot.worksheet.update(f"A{new_row}:I{new_row}", row_data, value_input_option='USER_ENTERED')
                logger.warning(f"Used fallback method for {username} - {class_name}/{spec}: {e}")
            except Exception as fallback_error:
                logger.error(f"Fallback method also failed for {username}: {fallback_error}")
                return False
        
        # Update role summary after saving
        await bot.update_role_summary()
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving to sheets: {e}")
        return False

@bot.tree.command(name="setclass", description="Set your WoW class and specialization")
@has_required_role()
@is_correct_channel()
async def set_class(interaction: discord.Interaction):
    """Main command to set class and spec"""
    try:
        if not bot.worksheet:
            await interaction.response.send_message(
                "❌ Database not available. Please try again later.", 
                ephemeral=True
            )
            return
    
        view = ClassSelectView()
        
        embed = discord.Embed(
            title="🎮 WoW Class Selection",
            description="Choose your World of Warcraft class from the dropdown below:",
            color=0x0099ff
        )
        embed.set_footer(text="You can change your selection at any time by running this command again.")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in set_class command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred. Please try again later.", 
            ephemeral=True
        )

@bot.tree.command(name="myclass", description="View your current class and specialization")
@has_required_role()
@is_correct_channel()
async def my_class(interaction: discord.Interaction):
    """Show user's current class selection"""
    try:
        if not bot.worksheet:
            await interaction.response.send_message(
                "❌ Database not available. Please try again later.", 
                ephemeral=True
            )
            return
        
        try:
            # Get all records and search for user
            all_records = bot.worksheet.get_all_records()
            user_record = None
        
            for record in all_records:
                # Check all possible columns where Discord ID might be stored
                found_user = False
                for key, value in record.items():
                    if str(value) == str(interaction.user.id):
                        user_record = record
                        found_user = True
                        break
                if found_user:
                    break
            
            if user_record:
                nickname = user_record.get('In-Game Name', 'Unknown')
                class_name = user_record.get('Class', 'Unknown')
                spec = user_record.get('Specialization', 'Unknown')
                last_updated = user_record.get('Last Updated', 'Unknown')
                update_count = user_record.get('Update Count', '1')
                
                embed = discord.Embed(
                    title="📋 Your Current Selection",
                    color=0x00ff00
                )
                embed.add_field(name="Character Name", value=nickname, inline=True)
                embed.add_field(name="Class", value=class_name, inline=True)
                embed.add_field(name="Specialization", value=spec, inline=True)
                embed.add_field(name="Last Updated", value=last_updated, inline=False)
                embed.add_field(name="Times Updated", value=str(update_count), inline=True)
                embed.set_footer(text="Use /setclass to change or /deleteclass to remove your selection")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                embed = discord.Embed(
                    title="📋 No Selection Found",
                    description="You haven't set your class and specialization yet.\nUse `/setclass` to make your selection!",
                    color=0xffaa00
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error reading user data: {e}")
            embed = discord.Embed(
                title="📋 No Selection Found",
                description="You haven't set your class and specialization yet.\nUse `/setclass` to make your selection!",
                color=0xffaa00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error in my_class command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred. Please try again later.", 
            ephemeral=True
        )

@bot.tree.command(name="classlist", description="View all available classes and specializations")
@has_required_role()
@is_correct_channel()
async def class_list(interaction: discord.Interaction):
    """Show all available classes and specs"""
    embed = discord.Embed(
        title="📚 Available Classes & Specializations",
        description="Here are all the available World of Warcraft classes and their specializations:",
        color=0x0099ff
    )
    
    for class_name, specs in CLASS_SPECS.items():
        spec_list = ", ".join(specs)
        embed.add_field(
            name=f"⚔️ {class_name}",
            value=spec_list,
            inline=False
        )
    
    embed.set_footer(text="Use /setclass to select your class and specialization")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="rolestats", description="View role distribution statistics")
@has_required_role()
@is_correct_channel()
async def role_stats(interaction: discord.Interaction):
    """Show role distribution statistics"""
    try:
        if not bot.summary_worksheet:
            await interaction.response.send_message(
                "❌ Summary data not available. Please try again later.", 
                ephemeral=True
            )
            return

        # Get summary data
        summary_records = bot.summary_worksheet.get_all_records()

        if not summary_records:
            await interaction.response.send_message(
                "📊 No role statistics available yet. Players need to set their classes first!", 
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📊 Role Distribution Statistics",
            description="Current breakdown of player roles in the community:",
            color=0x00ff00
        )

        total_players = 0
        role_emojis = {
            "Tank": "🛡️",
            "Healer": "💚", 
            "Melee DPS": "⚔️",
            "Ranged DPS": "🏹"
        }

        for record in summary_records:
            role = record.get('Role', '')
            count = record.get('Count', 0)
            percentage = record.get('Percentage', '0%')
            popular_class = record.get('Most Popular Class', 'None')
            popular_spec = record.get('Most Popular Spec', 'None')

            if role == "TOTAL":
                total_players = count
                continue

            if role in role_emojis:
                emoji = role_emojis[role]
                embed.add_field(
                    name=f"{emoji} {role}",
                    value=f"**{count}** players ({percentage})\n*Popular:* {popular_class}\n*Top Spec:* {popular_spec}",
                    inline=True
                )

        embed.add_field(
            name="👥 Total Players",
            value=f"**{total_players}** registered",
            inline=False
        )

        # Get last updated time
        if summary_records:
            last_updated = summary_records[0].get('Last Updated', 'Unknown')
            embed.set_footer(text=f"Last updated: {last_updated}")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Error in role_stats command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred while retrieving statistics. Please try again later.", 
            ephemeral=True
        )

@bot.tree.command(name="refreshstats", description="Manually refresh role statistics")
@has_required_role()
@is_correct_channel()  
async def refresh_stats(interaction: discord.Interaction):
    """Manually refresh role statistics"""
    try:
        await interaction.response.defer(ephemeral=True)

        if not bot.worksheet or not bot.summary_worksheet:
            await interaction.followup.send(
                "❌ Database not available. Please try again later."
            )
            return

        await bot.update_role_summary()

        embed = discord.Embed(
            title="✅ Statistics Refreshed!",
            description="Role distribution statistics have been updated.",
            color=0x00ff00,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Use /rolestats to view the updated statistics")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"Error in refresh_stats command: {e}")
        await interaction.followup.send(
            "❌ An error occurred while refreshing statistics. Please try again later."
        )

@bot.tree.command(name="deleteclass", description="Delete your class and specialization selection")
@has_required_role()
@is_correct_channel()
async def delete_class(interaction: discord.Interaction):
    """Delete user's class selection"""
    try:
        if not bot.worksheet:
            await interaction.response.send_message(
                "❌ Database not available. Please try again later.", 
                ephemeral=True
            )
            return
        
        # Check if user has a selection
        all_records = bot.worksheet.get_all_records()
        user_found = False
        row_num = 0
        
        for idx, record in enumerate(all_records):
            # Check all possible columns where Discord ID might be stored
            found_user = False
            for key, value in record.items():
                if str(value) == str(interaction.user.id):
                    user_found = True
                    row_num = idx + 2  # +2 because records start from row 2 (after header)
                    found_user = True
                    break
            if found_user:
                break
        
        if not user_found:
            embed = discord.Embed(
                title="❌ No Selection Found",
                description="You don't have any class selection to delete.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create confirmation view
        view = DeleteConfirmView(row_num, interaction.user)
        embed = discord.Embed(
            title="⚠️ Confirm Deletion",
            description="Are you sure you want to delete your class selection?\n\n**This action cannot be undone.**",
            color=0xffaa00
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in delete_class command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred. Please try again later.", 
            ephemeral=True
        )

@bot.tree.command(name="removeuser", description="[ADMIN] Remove a user's class selection")
@has_admin_role()
@is_correct_channel()
async def remove_user(interaction: discord.Interaction, user: discord.Member):
    """Admin command to remove a user's selection"""
    try:
        if not bot.worksheet:
            await interaction.response.send_message(
                "❌ Database not available. Please try again later.", 
                ephemeral=True
            )
            return
        
        # Check if user has a selection
        all_records = bot.worksheet.get_all_records()
        user_found = False
        row_num = 0
        user_data = None
        
        for idx, record in enumerate(all_records):
            # Check all possible columns where Discord ID might be stored
            found_user = False
            for key, value in record.items():
                if str(value) == str(user.id):
                    user_found = True
                    row_num = idx + 2  # +2 because records start from row 2 (after header)
                    user_data = record
                    found_user = True
                    break
            if found_user:
                break
        
        if not user_found:
            embed = discord.Embed(
                title="❌ User Not Found",
                description=f"{user.display_name} doesn't have any class selection to remove.",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create admin confirmation view
        view = AdminRemoveConfirmView(row_num, user, user_data)
        embed = discord.Embed(
            title="⚠️ Admin Confirmation",
            description=f"Remove class selection for **{user.display_name}**?\n\n**Character:** {user_data.get('In-Game Name', 'Unknown')}\n**Class:** {user_data.get('Class', 'Unknown')} {user_data.get('Specialization', 'Unknown')}\n\n**This action cannot be undone.**",
            color=0xffaa00
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in remove_user command: {e}")
        await interaction.response.send_message(
            "❌ An error occurred. Please try again later.", 
            ephemeral=True
        )

class DeleteConfirmView(discord.ui.View):
    def __init__(self, row_num: int, user: discord.User):
        super().__init__(timeout=60)
        self.row_num = row_num
        self.user = user
    
    @discord.ui.button(label="✅ Yes, Delete", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("You can't use this button!", ephemeral=True)
            return
        
        try:
            # Delete the row
            bot.worksheet.delete_rows(self.row_num)
            
            # Update role summary
            await bot.update_role_summary()
            
            embed = discord.Embed(
                title="✅ Selection Deleted",
                description="Your class selection has been successfully deleted.",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="You can set a new selection anytime with /setclass")
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Error deleting user selection: {e}")
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="❌ Error",
                    description="Failed to delete your selection. Please try again later.",
                    color=0xff0000
                ),
                view=None
            )
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("You can't use this button!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Cancelled",
            description="Deletion cancelled. Your selection remains unchanged.",
            color=0x808080
        )
        await interaction.response.edit_message(embed=embed, view=None)

class AdminRemoveConfirmView(discord.ui.View):
    def __init__(self, row_num: int, target_user: discord.Member, user_data: dict):
        super().__init__(timeout=60)
        self.row_num = row_num
        self.target_user = target_user
        self.user_data = user_data
    
    @discord.ui.button(label="✅ Remove User", style=discord.ButtonStyle.danger)
    async def confirm_remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Delete the row
            bot.worksheet.delete_rows(self.row_num)
            
            # Update role summary
            await bot.update_role_summary()
            
            embed = discord.Embed(
                title="✅ User Removed",
                description=f"Successfully removed {self.target_user.display_name}'s class selection.",
                color=0x00ff00,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Removed Data", value=f"**Character:** {self.user_data.get('In-Game Name', 'Unknown')}\n**Class:** {self.user_data.get('Class', 'Unknown')} {self.user_data.get('Specialization', 'Unknown')}", inline=False)
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Error removing user selection: {e}")
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="❌ Error",
                    description="Failed to remove user selection. Please try again later.",
                    color=0xff0000
                ),
                view=None
            )
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Cancelled",
            description="User removal cancelled.",
            color=0x808080
        )
        await interaction.response.edit_message(embed=embed, view=None)

# Error handlers
@set_class.error
@my_class.error
@class_list.error
@role_stats.error
@refresh_stats.error
@delete_class.error
@remove_user.error
async def command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        if CHANNEL_ID and interaction.channel_id != CHANNEL_ID:
            channel = bot.get_channel(CHANNEL_ID)
            channel_mention = f"<#{CHANNEL_ID}>" if channel else f"the designated channel"
            await interaction.response.send_message(
                f"❌ This command can only be used in {channel_mention}!", 
                ephemeral=True
            )
        elif REQUIRED_ROLE:
            await interaction.response.send_message(
                f"❌ You need the `{REQUIRED_ROLE}` role to use this command!", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ You don't have permission to use this command!", 
                ephemeral=True
            )
    else:
        logger.error(f"Command error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An unexpected error occurred. Please try again later.", 
                ephemeral=True
            )

# Run the bot
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN environment variable not set!")
        exit(1)
    
    bot.run(DISCORD_TOKEN)