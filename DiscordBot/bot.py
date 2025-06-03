# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report, State, ReportReason
import pdb
import openai
import time

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Load configuration from tokens.json
token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tokens.json')
if not os.path.isfile(token_path):
    print(f"Error: {token_path} not found!")
    print(f"Current working directory: {os.getcwd()}")
    print("Make sure to create a tokens.json file with your Discord token.")
    print("Format should be: { \"discord\": \"your_token_here\", \"openai\": \"your_openai_key_here\" }")
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    tokens = json.load(f)
    discord_token = tokens['discord']
    # Configure OpenAI API key if available
    if 'openai' in tokens:
        openai.api_key = tokens['openai']
    else:
        print("Warning: OpenAI API key not found in tokens.json")
        print("Add an 'openai' field with your API key to enable hate speech detection")
        openai.api_key = None

class ModBot(commands.Bot):
    """
    Discord bot for content moderation with hate speech detection capabilities.
    Handles message reporting, automated content analysis, and moderation actions.
    """
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {}  # Map from guild to the mod channel id for that guild
        self.reports = {}  # Map from user IDs to the state of their report
        self.mod_reports = {}  # Map from mod message IDs to reported message info
        self.message_report_counts = {}  # Map from message IDs to the number of times they've been reported
        self.user_offense_counts = {}  # Map from user IDs to the number of times they've been flagged for hate speech
        
        # Setting to control whether to forward clean messages (non-flagged) to mod channel
        self.forward_clean_messages = False  # Only forward flagged messages by default

        self.escalated_reports = {}
        self.escalation_channel_id = None
        self.law_enforcement_reports = {}  # Track LE escalations with reference IDs

        self.number_of_false_reports = {}
    
    async def setup_hook(self):
        """Load in moderator flow"""
        await self.load_extension('moderation')

    async def on_ready(self):
        """
        Called when the bot has successfully connected to Discord.
        Sets up the group number and mod channels.
        """
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
                    print(f"Found mod channel in {guild.name}: #{channel.name}")

    async def on_message(self, message):
        """
        Main message handler - processes all incoming messages.
        Ignores bot's own messages and routes to appropriate handlers.
        """
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Route to appropriate handler based on message source
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def get_text_from_attachment(self, attachment):
        """
        Downloads and reads text from a .txt file attachment.
        
        Args:
            attachment: The Discord attachment object
            
        Returns:
            str: The content of the text file, or None if it cannot be read
        """
        if not attachment.filename.lower().endswith('.txt'):
            return None
            
        try:
            # Download the attachment
            file_content = await attachment.read()
            # Convert bytes to string, assuming UTF-8 encoding
            text = file_content.decode('utf-8')
            return text
        except Exception as e:
            print(f"Error reading attachment: {e}")
            return None

    async def handle_dm(self, message):
        """
        Processes direct messages to the bot, primarily for reporting functionality.
        Handles the report flow and forwards completed reports to moderators.
        """
        # Handle help command
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow or starting one
        if message.content.lower() == Report.START_KEYWORD:
            self.reports[author_id] = Report(self)
        elif author_id not in self.reports:
            return

        # Let the report class handle this message and send responses
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # Forward complete reports to mod channels
        if author_id in self.reports and self.reports[author_id].state == State.REPORT_COMPLETE and self.reports[author_id].reason:
            # Find the guild that contains the reported message
            guild_id = self.reports[author_id].message.guild.id
            if guild_id in self.mod_channels:
                report = self.reports[author_id]
                reported_message_id = report.message.id
        
                # Update the report count for this message
                if reported_message_id not in self.message_report_counts:
                    self.message_report_counts[reported_message_id] = 1
                else:
                    self.message_report_counts[reported_message_id] += 1

                # Format the reason text with hate speech type if applicable
                reason_text = report.reason.value
                if report.reason == ReportReason.HATE_SPEECH and report.hate_speech_type:
                    reason_text += f" - {report.hate_speech_type.value}"

                # Send report to moderators
                moderation_cog = self.get_cog('Moderation')
                await moderation_cog.send_actionable_report_to_mods(
                    guild_id, 
                    report.message, 
                    message.author,
                    reason_text,
                    self.message_report_counts[reported_message_id],
                    is_user_report=True
                )

        # Clean up completed reports
        if author_id in self.reports and self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id:
            return
        
        guild = self.get_guild(payload.guild_id)
        if not guild: return
        
        user = await guild.fetch_member(payload.user_id)
        if not user: return

        moderation_cog = self.get_cog('Moderation')
        if not moderation_cog:
            return
  
        if payload.message_id in self.mod_reports:
            report_info = self.mod_reports[payload.message_id]
            if payload.emoji.name == '⏫':
                await moderation_cog.escalate_report(payload.message_id, report_info, user, guild)
            
            elif payload.emoji.name == '🚔':
                ref_id = await moderation_cog.escalate_to_law_enforcement(report_info, user, guild)
                await self.mod_channels[guild.id].send(
                    f"✅ Report escalated to law enforcement by {user.name}\n"
                    f"Reference ID: `{ref_id}`"
                )
        
        elif payload.emoji.name in ['🚔','✅', '❌']:
            await moderation_cog.handle_le_escalation_reaction(payload, user, guild)

    async def generate_incident_report(self, escalation_record, requesting_user, guild):      
        report_info = escalation_record['original_report']
        reported_msg = report_info['reported_message']
        
        incident_report = f"""
        **INCIDENT REPORT - {escalation_record['reference_id']}**
        **Generated by**: {requesting_user.name}
        **Generated at**: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

        **INCIDENT SUMMARY**:
        • Reference ID: {escalation_record['reference_id']}
        • Original Report: {report_info['reason']}
        • Escalated by: {escalation_record['escalated_by']}
        • Escalation Time: {escalation_record['escalated_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}
        • Current Status: {escalation_record['status']}

        **USER INFORMATION**:
        • Username: {reported_msg.author.name}
        • User ID: {reported_msg.author.id}
        • Account Created: {reported_msg.author.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
        • Previous Violations: {self.user_offense_counts.get(reported_msg.author.id, 0)}

        **MESSAGE DETAILS**:
        • Content: "{reported_msg.content}"
        • Channel: #{reported_msg.channel.name}
        • Message ID: {reported_msg.id}
        • Timestamp: {reported_msg.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

        **SERVER INFORMATION**:
        • Server Name: {guild.name}
        • Server ID: {guild.id}
        • Member Count: {guild.member_count}

        **LAW ENFORCEMENT CONTACT INFO**:
        • Discord Government Request Portal: https://app.kodexglobal.com/discord/signin
        • For emergencies: Contact local authorities immediately
        • For non-emergencies: Use the portal above with this Reference ID

        **EVIDENCE PRESERVATION**:
        • Original message preserved in server
        • All moderation actions documented
        • User history tracked in bot database
        """
            
        await self.mod_channels[guild.id].send(
            f"📋 **INCIDENT REPORT GENERATED**\n"
            f"``````\n"
            f"*Copy this report for law enforcement documentation*"
        )
        
        escalation_record['incident_report_generated'] = True
        escalation_record['report_generated_by'] = requesting_user.name
        escalation_record['report_generated_at'] = discord.utils.utcnow()


    async def handle_channel_message(self, message):
        """
        Processes messages in server channels.
        Handles moderation commands, analyzes content for hate speech,
        and forwards relevant messages to the mod channel.
        """
        # Handle moderator commands (replies to reported messages)
        if ((message.channel.name == f'group-{self.group_num}-mod' or 
             message.channel.name == f'group-{self.group_num}-escalation') and 
             message.reference):
            
            moderation_cog = self.get_cog('Moderation')
            if not moderation_cog:
                return

            referenced_message = await message.channel.fetch_message(message.reference.message_id)
            if referenced_message.id in self.mod_reports:
                action = message.content.lower()
                reported_info = self.mod_reports[referenced_message.id]
                reported_user = reported_info['reported_message'].author
                reporter = reported_info['reporter']
                
                if action == "ban":
                    await moderation_cog.execute_ban(reported_user, reported_info, message)      
                elif action == "warn":
                    await moderation_cog.execute_warn(reported_user, reported_info, message)
                elif action == "ban reporter":
                    if reported_info['is_user_report']:
                        await moderation_cog.execute_ban_reporter(reporter, reported_info, message)
                    else:
                        await message.channel.send("Cannot ban AutoMod reporter.")
                elif action == "warn reporter":
                    if reported_info['is_user_report']:
                        await moderation_cog.execute_warn_reporter(reporter, reported_info, message)
                    else:
                        await message.channel.send("Cannot warn AutoMod reporter.")
                elif action == "dismiss":
                    await moderation_cog.dismiss_report(reporter, reported_info, message)
                elif action == "toggle forwarding":
                    self.forward_clean_messages = not self.forward_clean_messages
                    status = "enabled" if self.forward_clean_messages else "disabled"
                    await message.channel.send(f"✅ Forwarding of clean messages is now {status}.")
                return

        # Only process messages from the group's channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        mod_channel = self.mod_channels[message.guild.id]
        
        # Track if any hate speech was detected in the message or attachments
        found_hate_speech = False
        
        # Process the text content of the message
        if message.content:
            scores = await self.eval_text(message.content)
            
            # Check if hate speech was detected in the message
            msg_has_hate = scores.get('hate_speech_detected', False)
            found_hate_speech = found_hate_speech or msg_has_hate
            
            # Forward message analysis to mod channel if appropriate
            moderation_cog = self.get_cog('Moderation')

            if msg_has_hate or self.forward_clean_messages:
                await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
                await mod_channel.send(self.code_format(scores))
            
            # Update user offense count and create actionable report if hate speech was detected
            if msg_has_hate:
                await self.update_user_offense_count(message.author, mod_channel)
                
                # Create an actionable report for moderators
                reason_text = f"Automatic hate speech detection"
                if scores.get("category"):
                    reason_text += f" - {scores.get('category')}"
                
                await moderation_cog.send_actionable_report_to_mods(
                    message.guild.id,
                    message,
                    "AutoMod",
                    reason_text,
                    is_user_report=False
                )
        
        # Process any attached text files
        for attachment in message.attachments:
            if attachment.filename.lower().endswith('.txt'):
                # Download and read the text from the .txt file
                file_text = await self.get_text_from_attachment(attachment)
                
                if file_text:
                    # Analyze the file content for hate speech
                    file_scores = await self.eval_text(file_text)
                    
                    # Check if hate speech was detected in the file
                    file_has_hate = file_scores.get('hate_speech_detected', False)
                    found_hate_speech = found_hate_speech or file_has_hate
                    
                    # Forward file analysis to mod channel if appropriate
                    if file_has_hate or self.forward_clean_messages:
                        await mod_channel.send(f'Processing attached file: {attachment.filename}')
                        await mod_channel.send(f'Analysis of {attachment.filename}:\n{self.code_format(file_scores)}')
                        
                        # Provide preview for long files
                        if len(file_text) > 500:
                            preview = file_text[:500] + "...(truncated)"
                            await mod_channel.send(f'File content preview (truncated):\n```\n{preview}\n```')
                    
                    # Update user offense count and create actionable report if hate speech was detected
                    if file_has_hate:
                        await self.update_user_offense_count(message.author, mod_channel)
                        
                        # Create an actionable report for moderators for file content
                        reason_text = f"Automatic hate speech detection in file ({attachment.filename})"
                        if file_scores.get("category"):
                            reason_text += f" - {file_scores.get('category')}"

                        moderation_cog = self.get_cog('ModerationCog')
                        await moderation_cog.send_actionable_report_to_mods(
                            message.guild.id,
                            message,
                            "AutoMod", 
                            reason_text,
                            is_user_report=False
                        )
                        
                elif self.forward_clean_messages:
                    await mod_channel.send(f'⚠️ Could not read text from {attachment.filename}')
        
        # Send alert if hate speech was detected but no content to display
        if found_hate_speech and not message.content and not any(a.filename.lower().endswith('.txt') for a in message.attachments):
            await mod_channel.send(f'⚠️ Hate speech detected in message from {message.author.name} but no content to display.')

    async def update_user_offense_count(self, user, mod_channel):
        """
        Updates and reports a user's offense count for hate speech.
        """
        # Initialize count if this is the first offense
        if user.id not in self.user_offense_counts:
            self.user_offense_counts[user.id] = 0
            
        # Increment the offense count
        self.user_offense_counts[user.id] += 1
        
        # Format offense count message based on number of offenses
        count = self.user_offense_counts[user.id]
        if count == 1:
            count_msg = "⚠️ This is their first offense."
        elif count == 2:
            count_msg = "⚠️⚠️ This is their second offense."
        elif count == 3:
            count_msg = "⚠️⚠️⚠️ This is their third offense. Consider taking stronger action."
        else:
            count_msg = f"⚠️ x{count} This user has {count} total offenses. Immediate action recommended!"
        
        # Send the offense count to the mod channel
        await mod_channel.send(f"**User Offense Tracking**: {user.name} (ID: {user.id})\n{count_msg}")
        
        # Recommend action based on offense count
        if count >= 3:
            await mod_channel.send("**Recommended Action**: Ban user for repeated hate speech violations.")
        elif count == 2:
            await mod_channel.send("**Recommended Action**: Issue a final warning to the user.")

    async def call_llm_for_hate_speech(self, text):
        """
        Calls an AI language model to evaluate text for hate speech.
        """
        if not openai.api_key:
            return {"error": "No OpenAI key found - can't check for hate speech", "hate_speech_detected": False}
            
        try:
            # Call the OpenAI API
            client = openai.OpenAI(api_key=openai.api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You're a content mod assistant. Analyze the text for hate speech. Respond in JSON with these fields: hate_speech_detected (boolean), confidence_score (number 0-1), category (string or null), explanation (string)."},
                    {"role": "user", "content": f"Check this text for hate speech: '{text}'"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=300
            )
            result = response.choices[0].message.content
            
            # Try to parse the JSON response
            try:
                import json
                return json.loads(result)
            except:
                # Simple error handling if parsing fails
                print(f"Couldn't parse API response: {result}")
                return {
                    "hate_speech_detected": False,
                    "confidence_score": 0,
                    "explanation": "Error processing API response",
                    "error": "Couldn't understand API response"
                }
                
        except Exception as e:
            print(f"API error: {e}")
            return {
                "error": f"API call failed: {str(e)}",
                "hate_speech_detected": False
            }
    
    async def eval_text(self, message):
        """
        Evaluates text for hate speech.
        """
        result = await self.call_llm_for_hate_speech(message)
        return result

    def code_format(self, analysis):
        """
        Formats the hate speech analysis results for display.
        """
        if isinstance(analysis, str):
            return f"Error: {analysis}"
            
        if "error" in analysis and analysis["error"]:
            return f"⚠️ Error checking text: {analysis['error']}"
            
        hate_detected = analysis.get("hate_speech_detected", False)
        confidence = analysis.get("confidence_score", "N/A")
        category = analysis.get("category", "N/A")
        explanation = analysis.get("explanation", "No explanation provided")
        
        if hate_detected:
            status = "🚨 **HATE SPEECH DETECTED**"
        else:
            status = "✅ No hate speech detected"
            
        formatted = f"{status}\n"
        formatted += f"**Confidence:** {confidence}\n"
        if category != "N/A" and category is not None:
            formatted += f"**Category:** {category}\n"
        formatted += f"**Analysis:** {explanation}"
            
        return formatted


# Initialize and run the bot
client = ModBot()
client.run(discord_token)