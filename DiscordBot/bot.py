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

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']

class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {}  # Map from guild to the mod channel id for that guild
        self.reports = {}  # Map from user IDs to the state of their report
        self.mod_reports = {}  # Map from mod message IDs to reported message info
        self.message_report_counts = {}  # Map from message IDs to the number of times they've been reported

    async def on_ready(self):
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
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
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

        # Let the report class handle this message; forward all the messages it returns to us
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # Forward report events to mod channels when complete
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

                reason_text = report.reason.value
                if report.reason == ReportReason.HATE_SPEECH and report.hate_speech_type:
                    reason_text += f" - {report.hate_speech_type.value}"

                mod_message = await self.mod_channels[guild_id].send(
                    f'New report from {message.author.name} via DM:\n'
                    f'Reason: {reason_text}\n'
                    f'Message: {report.message.author.name}: "{report.message.content}"\n'
                    f'This message has been reported {self.message_report_counts[reported_message_id]} time(s).\n'
                    f'\nModerators can reply with "Ban" or "Warn" to take action.'
                )
                
                # Store the report information
                self.mod_reports[mod_message.id] = {
                    'reported_message': report.message,
                    'reporter': message.author,
                    'reason': reason_text,
                    'report_count': self.message_report_counts[reported_message_id]
                }

        # If the report is complete or cancelled, remove it from our map
        if author_id in self.reports and self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Check if this is a mod response to a report
        if message.channel.name == f'group-{self.group_num}-mod' and message.reference:
            referenced_message = await message.channel.fetch_message(message.reference.message_id)
            if referenced_message.id in self.mod_reports:
                action = message.content.lower()
                reported_info = self.mod_reports[referenced_message.id]
                reported_user = reported_info['reported_message'].author
                
                if action == "ban":
                    try:
                        # Instead of banning, just send a DM
                        await reported_user.send(f"⛔ You have been banned for: {reported_info['reason']}")
                        await reported_info['reported_message'].delete()
                        await message.channel.send(f"✅ Simulated ban message sent to {reported_user.name}.")
                        if isinstance(reported_info['reporter'], discord.Member):
                            await reported_info['reporter'].send(f"The user you reported has been banned. Thank you for helping keep our community safe!")
                    except discord.Forbidden:
                        await message.channel.send("❌ I couldn't send a message to that user (they may have DMs disabled).")
                    
                elif action == "warn":
                    try:
                        await reported_user.send(f"⚠️ You have received a warning for: {reported_info['reason']}. If this happens again you will be banned.")
                        await reported_info['reported_message'].delete()
                        await message.channel.send(f"✅ Warning sent to {reported_user.name}.")
                        if isinstance(reported_info['reporter'], discord.Member):
                            await reported_info['reporter'].send(f"The user you reported has been warned. Thank you for helping keep our community safe!")
                    except discord.Forbidden:
                        await message.channel.send("❌ I couldn't send a warning to that user (they may have DMs disabled).")
                return

        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # Check if this is a "report" reply to another message
        if message.reference and message.content.lower() == Report.START_KEYWORD:
            try:
                referenced_message = await message.channel.fetch_message(message.reference.message_id)
                # Start a report flow with the referenced message
                self.reports[message.author.id] = Report(self, referenced_message)
                responses = await self.reports[message.author.id].handle_message(message)
                for r in responses:
                    await message.channel.send(r)
                
                # If the report is complete and has a reason, forward to mod channel
                report = self.reports[message.author.id]
                if report.state == State.REPORT_COMPLETE and report.reason:
                    reason_text = report.reason.value
                    if report.reason == ReportReason.HATE_SPEECH and report.hate_speech_type:
                        reason_text += f" - {report.hate_speech_type.value}"
                    
                    mod_message = await self.mod_channels[message.guild.id].send(
                        f'New report from {message.author.name} via reply:\n'
                        f'Reason: {reason_text}\n'
                        f'Message: {report.message.author.name}: "{report.message.content}"\n'
                        f'\nModerators can reply with "Ban" or "Warn" to take action.'
                    )
                    
                    # Store the report information
                    self.mod_reports[mod_message.id] = {
                        'reported_message': report.message,
                        'reporter': message.author,
                        'reason': reason_text
                    }
                
                # If the report is complete, remove it from our map
                if report.report_complete():
                    self.reports.pop(message.author.id)
                return
            except discord.errors.NotFound:
                await message.channel.send("I couldn't find the message you're trying to report. It may have been deleted.")
                return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        scores = self.eval_text(message.content)
        await mod_channel.send(self.code_format(scores))

    
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return message

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"


client = ModBot()
client.run(discord_token)