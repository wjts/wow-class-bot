import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import logging
from .config import GOOGLE_CREDENTIALS_FILE, SPREADSHEET_NAME

logger = logging.getLogger(__name__)

def log_user_action(user_id, username, action, details=""):
    """Log user actions with user information"""
    logger.info(f"USER ACTION - {username} (ID: {user_id}) - {action} - {details}")

def log_admin_action(admin_id, admin_username, action, target_user_id=None, target_username=None, details=""):
    """Log admin actions with admin and target information"""
    if target_user_id and target_username:
        logger.info(f"ADMIN ACTION - {admin_username} (ID: {admin_id}) - {action} - Target: {target_username} (ID: {target_user_id}) - {details}")
    else:
        logger.info(f"ADMIN ACTION - {admin_username} (ID: {admin_id}) - {action} - {details}")

class SheetsHandler:
    def __init__(self):
        self.google_sheet = None
        self.worksheet = None
    
    async def setup(self):
        """Set up Google Sheets connection"""
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
                logger.error(f"Google credentials file {GOOGLE_CREDENTIALS_FILE} not found!")
                return False
            
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
                logger.info("Created new worksheet with headers")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Google Sheets: {e}")
            return False
    
    async def save_user_selection(self, user_id: int, username: str, display_name: str,
                                 nickname: str, class_name: str, spec: str) -> bool:
        """Save user selection to Google Sheets"""
        try:
            if not self.worksheet:
                logger.error("Google Sheets not set up properly")
                return False
            
            # Get all records to check if user exists
            try:
                # Check if user already exists
                all_records = self.worksheet.get_all_records()
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
                    self.worksheet.update(f"A{row_num}:I{row_num}", row_data, value_input_option='USER_ENTERED')
                    
                    logger.info(f"Updated user {username} - {class_name}/{spec}")
                    log_user_action(user_id, username, "SELECTION_UPDATED", f"Character: {nickname}, Class: {class_name} {spec}, Update #{update_count}")
                else:
                    # Add new entry using batch update
                    new_row = len(all_records) + 2  # +2 for header row
                    row_data = [
                        [str(user_id), username, display_name, nickname, class_name, 
                         spec, current_time, 1, "Initial selection"]
                    ]
                    self.worksheet.update(f"A{new_row}:I{new_row}", row_data, value_input_option='USER_ENTERED')
                    
                    logger.info(f"Added new user {username} - {class_name}/{spec}")
                    log_user_action(user_id, username, "SELECTION_CREATED", f"Character: {nickname}, Class: {class_name} {spec}")
            
            except Exception as e:
                # Fallback: add new row using batch update
                try:
                    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                    # Find the next available row
                    all_values = self.worksheet.get_all_values()
                    new_row = len(all_values) + 1
                    
                    row_data = [
                        [str(user_id), username, display_name, nickname, class_name, 
                         spec, current_time, 1, "Selection (fallback)"]
                    ]
                    self.worksheet.update(f"A{new_row}:I{new_row}", row_data, value_input_option='USER_ENTERED')
                    logger.warning(f"Used fallback method for {username} - {class_name}/{spec}: {e}")
                    log_user_action(user_id, username, "SELECTION_SAVED_FALLBACK", f"Character: {nickname}, Class: {class_name} {spec} - Fallback due to: {e}")
                except Exception as fallback_error:
                    logger.error(f"Fallback method also failed for {username}: {fallback_error}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving to sheets: {e}")
            return False
    
    async def get_user_selection(self, user_id: int) -> dict:
        """Get user's current selection"""
        try:
            if not self.worksheet:
                return None
            
            # Get all records and search for user
            all_records = self.worksheet.get_all_records()
            
            for record in all_records:
                # Check all possible columns where Discord ID might be stored
                found_user = False
                for key, value in record.items():
                    if str(value) == str(user_id):
                        return record
                        
            return None
            
        except Exception as e:
            logger.error(f"Error getting user selection: {e}")
            return None
    
    async def delete_user_selection(self, user_id: int) -> tuple[bool, int]:
        """Delete user's selection, returns (success, row_number)"""
        try:
            if not self.worksheet:
                return False, 0
            
            # Get all records and find user
            all_records = self.worksheet.get_all_records()
            
            for idx, record in enumerate(all_records):
                # Check all possible columns where Discord ID might be stored
                found_user = False
                for key, value in record.items():
                    if str(value) == str(user_id):
                        row_num = idx + 2  # +2 because records start from row 2 (after header)
                        # Log before deletion to capture user info
                        username = record.get('Username', 'Unknown')
                        character_name = record.get('In-Game Name', 'Unknown')
                        class_name = record.get('Class', 'Unknown')
                        spec = record.get('Specialization', 'Unknown')
                        
                        self.worksheet.delete_rows(row_num)
                        logger.info(f"Deleted user selection at row {row_num}")
                        log_user_action(user_id, username, "SELECTION_DELETED", f"Character: {character_name}, Class: {class_name} {spec}")
                        return True, row_num
                        
            return False, 0
            
        except Exception as e:
            logger.error(f"Error deleting user selection: {e}")
            return False, 0