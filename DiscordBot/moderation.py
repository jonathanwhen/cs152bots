# moderation.py
import discord
from discord.ext import commands
import time

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_actionable_report_to_mods(self, guild_id, reported_message, reporter, reason, report_count=1, is_user_report=True):
        if guild_id in self.bot.mod_channels:
            if is_user_report:
                reporter_text = f"from {reporter.name} via DM"
                reporter_id = reporter.id
            else:
                reporter_text = "from automatic detection"
                reporter_id = None
            
            reported_user_offenses = self.bot.user_offense_counts.get(reported_message.author.id, 0)
            reported_user_suspensions = self.bot.user_suspension_counts.get(reported_message.author.id, 0)
            reporter_offenses = self.bot.user_offense_counts.get(reporter_id, 0) if reporter_id else 0
            reporter_suspensions = self.bot.user_suspension_counts.get(reporter_id, 0) if reporter_id else 0
            reporter_mistakes = self.bot.number_of_false_reports.get(reporter_id, 0) if reporter_id else 0
                
            mod_message = await self.bot.mod_channels[guild_id].send(
                f'New report {reporter_text}:\n'
                f'Reason: {reason}\n'
                f'Message: {reported_message.author.name}: "{reported_message.content}"\n'
                f'This message has been reported {report_count} time(s).\n\n'
                f'**Offense counts**:\n'
                f'• Reported User ({reported_message.author.name}): {reported_user_suspensions} suspensions(s)\n'
                f'• Reported User ({reported_message.author.name}): {reported_user_offenses} warning(s)\n\n'
                f'• Reporter ({reporter.name if is_user_report else "AutoMod"}): {reporter_suspensions} suspension(s)\n'
                f'• Reporter ({reporter.name if is_user_report else "AutoMod"}): {reporter_offenses} warning(s)\n'
                f'• Reporter ({reporter.name if is_user_report else "AutoMod"}): {reporter_mistakes} incorrect reports\n\n'
                f'\n**Moderation Options:**\n'
                f'• Reply with "Ban" to ban the reported user\n'
                f'• Reply with "Suspend" to suspend the reported user\n'
                f'• Reply with "Warn" to warn the reported user\n'
                f'• Reply with "Ban Reporter" to ban the reporter\n'
                f'• Reply with "Suspend Reporter" to suspend the reporter\n'
                f'• Reply with "Warn Reporter" to warn the reporter\n'
                f'• React with ⏫ for standard escalation\n'
                f'• React with 🚔 for law enforcement escalation\n'
                f'• Reply with "Dismiss" to dismiss report\n'
            )
            
            await mod_message.add_reaction('⏫')
            await mod_message.add_reaction('🚔')
            
            self.bot.mod_reports[mod_message.id] = {
                'reported_message': reported_message,
                'reporter': reporter,
                'reason': reason,
                'report_count': report_count,
                'is_user_report': is_user_report
            }
            
            return mod_message
        return None

    async def escalate_report(self, original_message_id, report_info, escalated_by, guild):
        if original_message_id in self.bot.escalated_reports:
            return
            
        self.bot.escalated_reports[original_message_id] = {
            'escalated_by': escalated_by,
            'escalated_at': discord.utils.utcnow(),
            'original_report': report_info
        }
        
        escalation_text = (
            f"🚨 **ESCALATED REPORT** 🚨\n"
            f"**Escalated by:** {escalated_by.name}\n"
            f"**Original reason:** {report_info['reason']}\n"
            f"**Reported user:** {report_info['reported_message'].author.name}\n"
            f"**Message content:** \"{report_info['reported_message'].content}\"\n"
            f"**Report count:** {report_info['report_count']} time(s)\n"
            f"**Needs senior moderator attention**\n\n"
            f"**Senior Moderator Options:**\n"
            f"• Reply with 'Ban', 'Warn', or 'Dismiss' to resolve\n"
            f"• Reply with 'Ban Reporter' or 'Warn Reporter' for malicious reporting\n"
            f"• React with 🚔 to escalate to law enforcement"
        )
        
        escalation_channel = None
        
        for channel in guild.text_channels:
            if channel.name == f'group-{self.bot.group_num}-escalation':
                escalation_channel = channel
                break
        
        if not escalation_channel:
            escalation_channel = self.bot.mod_channels[guild.id]
            escalation_text = f"@here {escalation_text}"
        
        escalation_message = await escalation_channel.send(escalation_text)
        await escalation_message.add_reaction('🚔')
        
        self.bot.mod_reports[escalation_message.id] = report_info.copy()
        self.bot.mod_reports[escalation_message.id]['is_escalated'] = True
        self.bot.mod_reports[escalation_message.id]['escalated_by'] = escalated_by.name
        
        original_channel = self.bot.mod_channels[guild.id]
        await original_channel.send(f"✅ Report escalated by {escalated_by.name}")

    async def escalate_to_law_enforcement(self, report_info, escalated_by, guild):
        reference_id = f"LE-{int(time.time())}-{report_info['reported_message'].id}"
        
        escalation_record = {
            'reference_id': reference_id,
            'escalated_at': discord.utils.utcnow(),
            'escalated_by': escalated_by.name,
            'original_report': report_info,
            'guild_id': guild.id,
            'status': 'pending_contact'
        }
        
        self.bot.law_enforcement_reports[reference_id] = escalation_record
        
        reported_msg = report_info['reported_message']
        
        le_notification = (
            f"🚨🚔 **LAW ENFORCEMENT ESCALATION** 🚔🚨\n"
            f"**Reference ID**: `{reference_id}`\n"
            f"**Escalated by**: {escalated_by.name}\n"
            f"**Timestamp**: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            
            f"**INCIDENT DETAILS**:\n"
            f"• **Reported User**: {reported_msg.author.name} (ID: `{reported_msg.author.id}`)\n"
            f"• **Message Content**: \"{reported_msg.content}\"\n"
            f"• **Channel**: #{reported_msg.channel.name}\n"
            f"• **Server**: {guild.name} (ID: `{guild.id}`)\n"
            f"• **Original Report**: {report_info['reason']}\n"
            f"• **Message Timestamp**: {reported_msg.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"• **User Offense History**: {self.bot.user_offense_counts.get(reported_msg.author.id, 0)} previous violations\n\n"
            
            f"**NEXT STEPS FOR MODERATORS**:\n"
            f"1. **Contact local law enforcement** if this involves immediate danger\n"
            f"2. **Use Discord's Government Request Portal** for non-emergency reports:\n"
            f"   https://app.kodexglobal.com/discord/signin\n"
            f"3. **Preserve all evidence** - do not delete the message yet\n"
            f"4. **Document any additional context** in this channel\n\n"
            
            f"**REACTIONS**:\n"
            f"🚔 - Confirm law enforcement has been contacted\n"
            f"✅ - Mark as resolved\n"
            f"❌ - Cancel escalation"
        )
        
        le_message = await self.bot.mod_channels[guild.id].send(le_notification)
        
        await le_message.add_reaction('🚔')
        await le_message.add_reaction('✅')
        await le_message.add_reaction('❌')
        
        escalation_record['message_id'] = le_message.id
        
        return reference_id

    async def execute_ban(self, reported_user, reported_info, mod_message):
        try:
            await reported_user.send(f"⛔ You have been banned for: {reported_info['reason']}")
            await reported_info['reported_message'].delete()
            
            if reported_info.get('is_escalated'):
                await mod_message.channel.send(f"✅ **ESCALATED REPORT RESOLVED** - Ban executed on {reported_user.name} by senior moderator.")
            else:
                await mod_message.channel.send(f"✅ Simulated ban message sent to {reported_user.name}.")
                
            if isinstance(reported_info['reporter'], discord.Member):
                await reported_info['reporter'].send(f"The user you reported has been banned. Thank you for helping keep our community safe!")
        except discord.Forbidden:
            await mod_message.channel.send("❌ I couldn't send a message to that user (they may have DMs disabled).")
    
    async def execute_suspend(self, reported_user, reported_info, mod_message):
        try:
            await reported_user.send(f"⚠️ You have received a warning for: {reported_info['reason']}. If this happens 3 times you will be banned.")
            await reported_info['reported_message'].delete()

            self.bot.user_suspension_counts[reported_user.id] = self.bot.user_suspension_counts.get(reported_user.id, 0) + 1
            
            if reported_info.get('is_escalated'):
                await mod_message.channel.send(f"✅ **ESCALATED REPORT RESOLVED** - Warning sent to {reported_user.name} by senior moderator.")
            else:
                await mod_message.channel.send(f"✅ Warning sent to {reported_user.name}.")
                
            if isinstance(reported_info['reporter'], discord.Member):
                await reported_info['reporter'].send(f"The user you reported has been warned. Thank you for helping keep our community safe!")
        except discord.Forbidden:
            await mod_message.channel.send("❌ I couldn't send a warning to that user (they may have DMs disabled).")


    async def execute_warn(self, reported_user, reported_info, mod_message):
        try:
            await reported_user.send(f"⚠️ You have received a warning for: {reported_info['reason']}. If this happens 3 times you will be suspended.")
            await reported_info['reported_message'].delete()

            self.bot.user_offense_counts[reported_user.id] = self.bot.user_offense_counts.get(reported_user.id, 0) + 1
            
            if reported_info.get('is_escalated'):
                await mod_message.channel.send(f"✅ **ESCALATED REPORT RESOLVED** - Warning sent to {reported_user.name} by senior moderator.")
            else:
                await mod_message.channel.send(f"✅ Warning sent to {reported_user.name}.")
                
            if isinstance(reported_info['reporter'], discord.Member):
                await reported_info['reporter'].send(f"The user you reported has been warned. Thank you for helping keep our community safe!")
        except discord.Forbidden:
            await mod_message.channel.send("❌ I couldn't send a warning to that user (they may have DMs disabled).")

    async def dismiss_report(self, reporter, reported_info, mod_message):
        print('here')
        await mod_message.channel.send(f"✅ **ESCALATED REPORT DISMISSED** - No action taken after senior review.")
        print('here2')
        self.bot.number_of_false_reports[reporter.id] = self.bot.number_of_false_reports.get(reporter.id, 0) + 1
        
        if reported_info.get('is_user_report') and isinstance(reported_info['reporter'], discord.Member):
            await reported_info['reporter'].send(f"Thank you for your report. After review, no action was deemed necessary, but we appreciate your vigilance in keeping our community safe.")
    

    async def execute_ban_reporter(self, reporter, reported_info, mod_message):
        try:
            await reporter.send(f"⛔ You have been banned for malicious reporting.")
    
            if reported_info.get('is_escalated'):
                await mod_message.channel.send(f"✅ **ESCALATED REPORT RESOLVED** - Ban executed on {reporter.name} by senior moderator.")
            else:
                await mod_message.channel.send(f"✅ Simulated ban message sent to {reporter.name}.")
                
        except discord.Forbidden:
            await mod_message.channel.send("❌ I couldn't send a message to that user (they may have DMs disabled).")
    
    async def execute_suspend_reporter(self, reporter, reported_info, mod_message):
        try:
            await reporter.send(f"⚠️ You have received a suspension for malicious reporting. If this happens again you will be banned.")

            self.bot.user_suspension_counts[reporter.id] = self.bot.user_suspension_counts.get(reporter.id, 0) + 1
            
            if reported_info.get('is_escalated'):
                await mod_message.channel.send(f"✅ **ESCALATED REPORT RESOLVED** - Warning sent to {reporter.name} by senior moderator.")
            else:
                await mod_message.channel.send(f"✅ Warning sent to {reporter.name}.")
                
        except discord.Forbidden:
            await mod_message.channel.send("❌ I couldn't send a warning to that user (they may have DMs disabled).")

    async def execute_warn_reporter(self, reporter, reported_info, mod_message):
        try:
            await reporter.send(f"⚠️ You have received a warning for malicious reporting. If this happens again you will be suspended.")

            self.bot.user_offense_counts[reporter.id] = self.bot.user_offense_counts.get(reporter.id, 0) + 1
            
            if reported_info.get('is_escalated'):
                await mod_message.channel.send(f"✅ **ESCALATED REPORT RESOLVED** - Warning sent to {reporter.name} by senior moderator.")
            else:
                await mod_message.channel.send(f"✅ Warning sent to {reporter.name}.")
                
        except discord.Forbidden:
            await mod_message.channel.send("❌ I couldn't send a warning to that user (they may have DMs disabled).")


    async def handle_le_escalation_reaction(self, payload, user, guild):
        escalation_record = None
        for ref_id, record in self.bot.law_enforcement_reports.items():
            if record.get('message_id') == payload.message_id:
                escalation_record = record
                break
        
        if not escalation_record:
            return
        
        if payload.emoji.name == '🚔':
            escalation_record['status'] = 'le_contacted'
            escalation_record['le_contacted_by'] = user.name
            escalation_record['le_contacted_at'] = discord.utils.utcnow()
            
            await self.bot.mod_channels[guild.id].send(
                f"✅ **Law enforcement contact confirmed** by {user.name}\n"
                f"Reference: `{escalation_record['reference_id']}`"
            )
        
        elif payload.emoji.name == '✅':
            escalation_record['status'] = 'resolved'
            escalation_record['resolved_by'] = user.name
            escalation_record['resolved_at'] = discord.utils.utcnow()
            
            await self.bot.mod_channels[guild.id].send(
                f"✅ **Law enforcement escalation resolved** by {user.name}\n"
                f"Reference: `{escalation_record['reference_id']}`"
            )
        
        elif payload.emoji.name == '❌':
            escalation_record['status'] = 'cancelled'
            escalation_record['cancelled_by'] = user.name
            escalation_record['cancelled_at'] = discord.utils.utcnow()
            
            await self.bot.mod_channels[guild.id].send(
                f"❌ **Law enforcement escalation cancelled** by {user.name}\n"
                f"Reference: `{escalation_record['reference_id']}`"
            )

async def setup(bot):
    await bot.add_cog(Moderation(bot))