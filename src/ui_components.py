import discord
from discord import app_commands
from datetime import datetime
from .config import CLASS_SPECS
import logging

logger = logging.getLogger(__name__)

def log_user_action(user, action, details=""):
    """Log user actions with user information"""
    logger.info(f"USER ACTION - {user.name}#{user.discriminator} (ID: {user.id}) - {action} - {details}")

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
        # Get sheets handler from bot
        bot = interaction.client
        sheets_handler = getattr(bot, 'sheets_handler', None)
        
        view = SpecSelectView(self.class_name, self.user, self.nickname.value, interaction)
        view.set_sheets_handler(sheets_handler)
        
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
    def __init__(self, class_name: str, nickname: str, modal_interaction, sheets_handler):
        self.class_name = class_name
        self.nickname = nickname
        self.modal_interaction = modal_interaction
        self.sheets_handler = sheets_handler
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
        success = await self.sheets_handler.save_user_selection(
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
            log_user_action(self.modal_interaction.user, "CLASS_SELECTION_SAVED", f"Character: {self.nickname}, Class: {self.class_name} {selected_spec}")
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="There was an error saving your selection. Please try again later.",
                color=0xff0000
            )
            log_user_action(self.modal_interaction.user, "CLASS_SELECTION_FAILED", f"Failed to save: {self.nickname}, {self.class_name} {selected_spec}")
        
        await interaction.edit_original_response(embed=embed, view=None)

class SpecSelectView(discord.ui.View):
    def __init__(self, class_name: str, user: discord.User, nickname: str, modal_interaction):
        super().__init__(timeout=300)
        self.class_name = class_name
        self.user = user
        self.nickname = nickname
        self.modal_interaction = modal_interaction
        # Note: sheets_handler will be set when this view is used
        
    def set_sheets_handler(self, sheets_handler):
        """Set the sheets handler and add the spec select"""
        self.add_item(SpecSelect(self.class_name, self.nickname, self.modal_interaction, sheets_handler))
    
    @discord.ui.button(label="🔙 Back to Classes", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.modal_interaction.user:
            await interaction.response.send_message("You can't use this button!", ephemeral=True)
            return
        
        view = ClassSelectView()
        embed = discord.Embed(
            title="🎮 WoW Class Selection",
            description="Choose your World of Warcraft class from the dropdown below:",
            color=0x0099ff
        )
        
        await interaction.response.edit_message(embed=embed, view=view)

class DeleteConfirmView(discord.ui.View):
    def __init__(self, user: discord.User, sheets_handler):
        super().__init__(timeout=60)
        self.user = user
        self.sheets_handler = sheets_handler
    
    @discord.ui.button(label="✅ Yes, Delete", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("You can't use this button!", ephemeral=True)
            return
        
        try:
            # Delete the user's selection
            success, row_num = await self.sheets_handler.delete_user_selection(self.user.id)
            
            if success:
                embed = discord.Embed(
                    title="✅ Selection Deleted",
                    description="Your class selection has been successfully deleted.",
                    color=0x00ff00,
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text="You can set a new selection anytime with /setclass")
                log_user_action(self.user, "SELECTION_DELETED", "User deleted their own class selection")
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to delete your selection. Please try again later.",
                    color=0xff0000
                )
                log_user_action(self.user, "DELETION_FAILED", "Failed to delete class selection")
            
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
        log_user_action(self.user, "DELETION_CANCELLED", "User cancelled deletion of their class selection")
        await interaction.response.edit_message(embed=embed, view=None)

class AdminRemoveConfirmView(discord.ui.View):
    def __init__(self, target_user: discord.Member, user_data: dict, sheets_handler):
        super().__init__(timeout=60)
        self.target_user = target_user
        self.user_data = user_data
        self.sheets_handler = sheets_handler
    
    @discord.ui.button(label="✅ Remove User", style=discord.ButtonStyle.danger)
    async def confirm_remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Delete the user's selection
            success, row_num = await self.sheets_handler.delete_user_selection(self.target_user.id)
            
            if success:
                embed = discord.Embed(
                    title="✅ User Removed",
                    description=f"Successfully removed {self.target_user.display_name}'s class selection.",
                    color=0x00ff00,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(
                    name="Removed Data", 
                    value=f"**Character:** {self.user_data.get('In-Game Name', 'Unknown')}\n**Class:** {self.user_data.get('Class', 'Unknown')} {self.user_data.get('Specialization', 'Unknown')}", 
                    inline=False
                )
                # Use a more specific admin logging function
                logger.info(f"ADMIN ACTION - {interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id}) - USER_REMOVED - Target: {self.target_user.name}#{self.target_user.discriminator} (ID: {self.target_user.id}) - Character: {self.user_data.get('In-Game Name', 'Unknown')}, Class: {self.user_data.get('Class', 'Unknown')} {self.user_data.get('Specialization', 'Unknown')}")
            else:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Failed to remove user selection. Please try again later.",
                    color=0xff0000
                )
                logger.error(f"ADMIN ACTION FAILED - {interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id}) - USER_REMOVAL_FAILED - Target: {self.target_user.name}#{self.target_user.discriminator} (ID: {self.target_user.id})")
            
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
        logger.info(f"ADMIN ACTION - {interaction.user.name}#{interaction.user.discriminator} (ID: {interaction.user.id}) - USER_REMOVAL_CANCELLED - Target: {self.target_user.name}#{self.target_user.discriminator} (ID: {self.target_user.id})")
        await interaction.response.edit_message(embed=embed, view=None)