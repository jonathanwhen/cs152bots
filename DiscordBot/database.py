import os
from supabase import create_client, Client
from datetime import datetime
import json
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class InfractionDatabase:
    def __init__(self):
        # Load configuration from tokens.json
        token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tokens.json')
        if not os.path.isfile(token_path):
            raise ValueError(f"Error: {token_path} not found!")
            
        with open(token_path) as f:
            tokens = json.load(f)
            
        # Get Supabase credentials
        url = tokens.get('supabase_url')
        key = tokens.get('supabase_key')
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in tokens.json")
            
        logger.info(f"Initializing Supabase connection to {url}")
        self.supabase: Client = create_client(url, key)
        logger.info("Supabase connection initialized successfully")
        
    async def add_infraction(self, user_id: int, user_name: str, infraction_type: str, 
                           reason: str, message_content: str, channel_id: int, 
                           message_id: int, guild_id: int, detected_by: str,
                           confidence: float = None, category: str = None):
        """
        Add a new infraction to the database.
        
        Args:
            user_id: Discord user ID
            user_name: Discord username
            infraction_type: Type of infraction (e.g., "hate_speech", "spam")
            reason: Detailed reason for the infraction
            message_content: Content of the offending message
            channel_id: Discord channel ID where the infraction occurred
            message_id: Discord message ID of the infraction
            guild_id: Discord guild (server) ID
            detected_by: Who/what detected the infraction (e.g., "automod", "user_report")
            confidence: Confidence score if detected by AI (optional)
            category: Category of the infraction if applicable (optional)
        """
        try:
            logger.debug(f"Attempting to add infraction for user {user_name} (ID: {user_id})")
            data = {
                "user_id": user_id,
                "user_name": user_name,
                "infraction_type": infraction_type,
                "reason": reason,
                "message_content": message_content,
                "channel_id": channel_id,
                "message_id": message_id,
                "guild_id": guild_id,
                "detected_by": detected_by,
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": confidence,
                "category": category
            }
            
            logger.debug(f"Inserting data: {json.dumps(data, indent=2)}")
            result = self.supabase.table("infractions").insert(data).execute()
            logger.info(f"Successfully added infraction. Result: {json.dumps(result.data, indent=2)}")
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Error adding infraction to database: {str(e)}", exc_info=True)
            return None
            
    async def get_user_infractions(self, user_id: int, guild_id: int = None):
        """
        Get all infractions for a specific user.
        
        Args:
            user_id: Discord user ID
            guild_id: Optional guild ID to filter by specific server
            
        Returns:
            List of infractions
        """
        try:
            query = self.supabase.table("infractions").select("*").eq("user_id", user_id)
            
            if guild_id:
                query = query.eq("guild_id", guild_id)
                
            result = query.execute()
            return result.data
            
        except Exception as e:
            print(f"Error fetching user infractions: {str(e)}")
            return []
            
    async def get_recent_infractions(self, guild_id: int, limit: int = 10):
        """
        Get recent infractions for a specific guild.
        
        Args:
            guild_id: Discord guild ID
            limit: Maximum number of infractions to return
            
        Returns:
            List of recent infractions
        """
        try:
            result = (self.supabase.table("infractions")
                     .select("*")
                     .eq("guild_id", guild_id)
                     .order("timestamp", desc=True)
                     .limit(limit)
                     .execute())
            return result.data
            
        except Exception as e:
            print(f"Error fetching recent infractions: {str(e)}")
            return []
            
    async def get_infraction_stats(self, guild_id: int):
        """
        Get statistics about infractions in a guild.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Dictionary containing infraction statistics
        """
        try:
            # Get total infractions
            total_result = (self.supabase.table("infractions")
                          .select("*", count="exact")
                          .eq("guild_id", guild_id)
                          .execute())
            
            # Get infractions by type
            type_result = (self.supabase.table("infractions")
                         .select("infraction_type", count="exact")
                         .eq("guild_id", guild_id)
                         .execute())
            
            # Get infractions by detection method
            detection_result = (self.supabase.table("infractions")
                              .select("detected_by", count="exact")
                              .eq("guild_id", guild_id)
                              .execute())
            
            return {
                "total_infractions": total_result.count,
                "by_type": type_result.data,
                "by_detection": detection_result.data
            }
            
        except Exception as e:
            print(f"Error fetching infraction stats: {str(e)}")
            return {
                "total_infractions": 0,
                "by_type": [],
                "by_detection": []
            }
            
    async def get_user_infraction_count(self, user_id: int, guild_id: int) -> int:
        """
        Get the number of infractions for a specific user in a guild.
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            
        Returns:
            Number of infractions
        """
        try:
            result = (self.supabase.table("infractions")
                     .select("*", count="exact")
                     .eq("user_id", user_id)
                     .eq("guild_id", guild_id)
                     .execute())
            return result.count if result.count is not None else 0
        except Exception as e:
            print(f"Error getting user infraction count: {str(e)}")
            return 0 