from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_REASON = auto()
    AWAITING_HATE_SPEECH_TYPE = auto()
    REPORT_COMPLETE = auto()

class ReportReason(Enum):
    HATE_SPEECH = "hate speech"
    SPAM = "spam"
    VIOLENT_ENTITIES = "violent and/or hateful entities"
    VIOLENT_SPEECH = "violent speech"
    OTHER = "other"

class HateSpeechType(Enum):
    HATEFUL_REFERENCES = "hateful references"
    SLURS = "slurs"
    HATEFUL_SYMBOLS = "hateful symbols/signs"
    DISCRIMINATION = "discrimination"
    DISCRIMINATORY_STEREOTYPES = "discriminatory stereotypes"

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    def __init__(self, client, reference_message=None):
        self.state = State.MESSAGE_IDENTIFIED if reference_message else State.REPORT_START
        self.client = client
        self.message = reference_message
        self.reason = None
        self.hate_speech_type = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                self.message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]
            self.state = State.MESSAGE_IDENTIFIED

        if self.state == State.MESSAGE_IDENTIFIED:
            # If we have a message (either from reference or link), show it and ask for reason
            if self.message:
                self.state = State.AWAITING_REASON
                reply = ["I found this message:", "```" + self.message.author.name + ": " + self.message.content + "```", \
                        "What is the reason for reporting this message? Please choose one of the following:", \
                        "1. hate speech", "2. spam", "3. violent and/or hateful entities", "4. violent speech", "5. other", \
                        "\nPlease respond with the number or the exact text of your choice."]
                return reply
        
        if self.state == State.AWAITING_REASON:
            # Accept either the number or the text of the reason
            reason_text = message.content.lower()
            if reason_text in ["1", "hate speech"]:
                self.reason = ReportReason.HATE_SPEECH
                self.state = State.AWAITING_HATE_SPEECH_TYPE
                return ["Please specify the type of hate speech. Choose one of the following:", \
                        "1. hateful references", "2. slurs", "3. hateful symbols/signs", \
                        "4. discrimination", "5. discriminatory stereotypes", \
                        "\nPlease respond with the number or the exact text of your choice."]
            elif reason_text in ["2", "spam"]:
                self.reason = ReportReason.SPAM
            elif reason_text in ["3", "violent and/or hateful entities"]:
                self.reason = ReportReason.VIOLENT_ENTITIES
            elif reason_text in ["4", "violent speech"]:
                self.reason = ReportReason.VIOLENT_SPEECH
            elif reason_text in ["5", "other"]:
                self.reason = ReportReason.OTHER
            else:
                return ["Please choose a valid reason by entering either the number (1-5) or the exact text of one of the options above."]
            
            self.state = State.REPORT_COMPLETE
            return [
                f"Thank you for your report. The message has been reported for: {self.reason.value}",
                "Thank you for your report and we appreciate you helping to make our platform better and safer! We will thoroughly investigate your report shortly. In the meantime, please consider muting or blocking the reported account."
            ]

        if self.state == State.AWAITING_HATE_SPEECH_TYPE:
            # Accept either the number or the text of the hate speech type
            type_text = message.content.lower()
            if type_text in ["1", "hateful references"]:
                self.hate_speech_type = HateSpeechType.HATEFUL_REFERENCES
            elif type_text in ["2", "slurs"]:
                self.hate_speech_type = HateSpeechType.SLURS
            elif type_text in ["3", "hateful symbols/signs"]:
                self.hate_speech_type = HateSpeechType.HATEFUL_SYMBOLS
            elif type_text in ["4", "discrimination"]:
                self.hate_speech_type = HateSpeechType.DISCRIMINATION
            elif type_text in ["5", "discriminatory stereotypes"]:
                self.hate_speech_type = HateSpeechType.DISCRIMINATORY_STEREOTYPES
            else:
                return ["Please choose a valid hate speech type by entering either the number (1-5) or the exact text of one of the options above."]
            
            self.state = State.REPORT_COMPLETE
            return [
                f"Thank you for your report. The message has been reported for {self.reason.value} - {self.hate_speech_type.value}",
                "Thank you for your report and we appreciate you helping to make our platofrm better and safer! We will thoroughly investigate your report shortly. In the meantime, please consider muting or blocking the reported account."
            ]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE





