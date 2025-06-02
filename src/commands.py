import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import logging
from .config import CLASS_SPECS, CHANNEL_ID, REQUIRED_ROLE, ADMIN_ROLE
from .ui_components import ClassSelectView, DeleteConfirmView, AdminRemoveConfirmView

logger = logging.getLogger(__name__)

def log_user_action(user, action, details=""):
    """Log user actions with user information"""
    logger.info(f"USER ACTION - {user.name}#{user.discriminator} (ID: {user.id}) - {action} - {details}")

def log_admin_action(admin, action, target_user=None, details=""):
    """Log admin actions with admin and target information"""
    if target_user:
        logger.info(f"ADMIN ACTION - {admin.name}#{admin.discriminator} (ID: {admin.id}) - {action} - Target: {target_user.name}#{target_user.discriminator} (ID: {target_user.id}) - {details}")
    else:
        logger.info(f"ADMIN ACTION - {admin.name}#{admin.discriminator} (ID: {admin.id}) - {action} - {details}")

def log_security_event(user, action, details=""):
    """Log security events (unauthorized attempts, etc.)"""
    logger.warning(f"SECURITY EVENT - {user.name}#{user.discriminator} (ID: {user.id}) - {action} - {details}")

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

class Commands:
    def __init__(self, bot, sheets_handler):
        self.bot = bot
        self.sheets_handler = sheets_handler
        self.setup_commands()
    
    def setup_commands(self):
        """Register all commands"""
        
        @self.bot.tree.command(name="setclass", description="Set or update your WoW class, specialization, and in-game character name")
        @has_required_role()
        @is_correct_channel()
        async def set_class(interaction: discord.Interaction):
            """Main command to set class and spec"""
            try:
                if not self.sheets_handler.worksheet:
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
                log_user_action(interaction.user, "STARTED_CLASS_SELECTION", "Opened class selection interface")
                
            except Exception as e:
                logger.error(f"Error in set_class command: {e}")
                log_user_action(interaction.user, "SET_CLASS_ERROR", f"Error: {e}")
                await interaction.response.send_message(
                    "❌ An error occurred. Please try again later.", 
                    ephemeral=True
                )

        @self.bot.tree.command(name="myclass", description="View your current class and specialization")
        @has_required_role()
        @is_correct_channel()
        async def my_class(interaction: discord.Interaction):
            """Show user's current class selection"""
            try:
                if not self.sheets_handler.worksheet:
                    await interaction.response.send_message(
                        "❌ Database not available. Please try again later.", 
                        ephemeral=True
                    )
                    return
                
                user_record = await self.sheets_handler.get_user_selection(interaction.user.id)
                
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
                    log_user_action(interaction.user, "VIEWED_CLASS_LIST", "Viewed available classes and specializations")
                    log_user_action(interaction.user, "VIEWED_SELECTION", f"Character: {nickname}, Class: {class_name} {spec}")
                else:
                    embed = discord.Embed(
                        title="📋 No Selection Found",
                        description="You haven't set your class and specialization yet.\nUse `/setclass` to make your selection!",
                        color=0xffaa00
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    log_user_action(interaction.user, "VIEWED_SELECTION", "No selection found")
                    
            except Exception as e:
                logger.error(f"Error in my_class command: {e}")
                log_user_action(interaction.user, "MY_CLASS_ERROR", f"Error: {e}")
                await interaction.response.send_message(
                    "❌ An error occurred. Please try again later.", 
                    ephemeral=True
                )

        @self.bot.tree.command(name="classlist", description="View all available classes and specializations")
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

        @self.bot.tree.command(name="deleteclass", description="Delete your class and specialization selection")
        @has_required_role()
        @is_correct_channel()
        async def delete_class(interaction: discord.Interaction):
            """Delete user's class selection"""
            try:
                if not self.sheets_handler.worksheet:
                    await interaction.response.send_message(
                        "❌ Database not available. Please try again later.", 
                        ephemeral=True
                    )
                    return
                
                # Check if user has a selection
                user_record = await self.sheets_handler.get_user_selection(interaction.user.id)
                
                if not user_record:
                    embed = discord.Embed(
                        title="❌ No Selection Found",
                        description="You don't have any class selection to delete.",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    log_user_action(interaction.user, "DELETE_ATTEMPT_FAILED", "No selection found to delete")
                    return
                
                # Create confirmation view
                view = DeleteConfirmView(interaction.user, self.sheets_handler)
                embed = discord.Embed(
                    title="⚠️ Confirm Deletion",
                    description="Are you sure you want to delete your class selection?\n\n**This action cannot be undone.**",
                    color=0xffaa00
                )
                
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                log_user_action(interaction.user, "INITIATED_DELETE", "Started deletion confirmation process")
                
            except Exception as e:
                logger.error(f"Error in delete_class command: {e}")
                log_user_action(interaction.user, "DELETE_CLASS_ERROR", f"Error: {e}")
                await interaction.response.send_message(
                    "❌ An error occurred. Please try again later.", 
                    ephemeral=True
                )

        @self.bot.tree.command(name="removeuser", description="[ADMIN] Remove a user's class selection")
        @has_admin_role()
        @is_correct_channel()
        async def remove_user(interaction: discord.Interaction, user: discord.Member):
            """Admin command to remove a user's selection"""
            try:
                if not self.sheets_handler.worksheet:
                    await interaction.response.send_message(
                        "❌ Database not available. Please try again later.", 
                        ephemeral=True
                    )
                    return
                
                # Check if user has a selection
                user_data = await self.sheets_handler.get_user_selection(user.id)
                
                if not user_data:
                    embed = discord.Embed(
                        title="❌ User Not Found",
                        description=f"{user.display_name} doesn't have any class selection to remove.",
                        color=0xff0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    log_admin_action(interaction.user, "REMOVE_USER_FAILED", user, "No selection found for target user")
                    return
                
                # Create admin confirmation view
                view = AdminRemoveConfirmView(user, user_data, self.sheets_handler)
                embed = discord.Embed(
                    title="⚠️ Admin Confirmation",
                    description=f"Remove class selection for **{user.display_name}**?\n\n**Character:** {user_data.get('In-Game Name', 'Unknown')}\n**Class:** {user_data.get('Class', 'Unknown')} {user_data.get('Specialization', 'Unknown')}\n\n**This action cannot be undone.**",
                    color=0xffaa00
                )
                
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                log_admin_action(interaction.user, "INITIATED_USER_REMOVAL", user, f"Character: {user_data.get('In-Game Name', 'Unknown')}, Class: {user_data.get('Class', 'Unknown')} {user_data.get('Specialization', 'Unknown')}")
                
            except Exception as e:
                logger.error(f"Error in remove_user command: {e}")
                log_admin_action(interaction.user, "REMOVE_USER_ERROR", user, f"Error: {e}")
                await interaction.response.send_message(
                    "❌ An error occurred. Please try again later.", 
                    ephemeral=True
                )

        # Error handlers
        @set_class.error
        @my_class.error
        @class_list.error
        @delete_class.error
        @remove_user.error
        async def command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            if isinstance(error, app_commands.CheckFailure):
                # Determine which command was attempted
                command_name = interaction.command.name if interaction.command else "unknown"
                
                if CHANNEL_ID and interaction.channel_id != CHANNEL_ID:
                    channel = self.bot.get_channel(CHANNEL_ID)
                    channel_mention = f"<#{CHANNEL_ID}>" if channel else f"the designated channel"
                    await interaction.response.send_message(
                        f"❌ This command can only be used in {channel_mention}!", 
                        ephemeral=True
                    )
                    log_security_event(interaction.user, "WRONG_CHANNEL_ATTEMPT", f"Tried to use /{command_name} in wrong channel")
                elif REQUIRED_ROLE:
                    # Check if this was an admin command attempt
                    if command_name == "removeuser":
                        log_security_event(interaction.user, "UNAUTHORIZED_ADMIN_ATTEMPT", f"Tried to use /{command_name} without admin role")
                    else:
                        log_security_event(interaction.user, "UNAUTHORIZED_ACCESS_ATTEMPT", f"Tried to use /{command_name} without required role")
                    
                    await interaction.response.send_message(
                        f"❌ You need the `{REQUIRED_ROLE}` role to use this command!", 
                        ephemeral=True
                    )
                else:
                    log_security_event(interaction.user, "PERMISSION_DENIED", f"Permission denied for /{command_name}")
                    await interaction.response.send_message(
                        "❌ You don't have permission to use this command!", 
                        ephemeral=True
                    )
            else:
                logger.error(f"Command error: {error}")
                command_name = interaction.command.name if interaction.command else "unknown"
                log_user_action(interaction.user, "COMMAND_ERROR", f"Error in /{command_name}: {error}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ An unexpected error occurred. Please try again later.", 
                        ephemeral=True
                    )