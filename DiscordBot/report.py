from enum import Enum, auto
import discord
import re
import openai
import os

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_REASON = auto()
    AWAITING_HATE_SPEECH_TYPE = auto()
    REPORT_COMPLETE = auto()
    AWAITING_CONFIRMATION = auto()

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

class HateSpeechClassifier:
    def __init__(self):
        # Initialize with your API key - ideally from environment variables for security
        openai.api_key = os.environ.get("OPENAI_API_KEY")
    
    async def classify_message(self, message_content):
        """
        Uses LLM to classify if a message contains hate speech and what type.
        Returns a tuple (is_hate_speech, hate_speech_type, confidence, explanation)
        """
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Or use another appropriate model
                messages=[
                    {"role": "system", "content": "You are an AI trained to detect and classify hate speech in messages."},
                    {"role": "user", "content": f"Analyze this message for hate speech: '{message_content}'. If it contains hate speech, specify the type (hateful references, slurs, hateful symbols/signs, discrimination, or discriminatory stereotypes) and provide a brief explanation. Format your response as: CONTAINS_HATE_SPEECH: [Yes/No], TYPE: [type if applicable], CONFIDENCE: [High/Medium/Low], EXPLANATION: [brief explanation]"}
                ]
            )
            
            result = response.choices[0].message.content
            
            # Parse the structured response
            contains_hate = "CONTAINS_HATE_SPEECH: Yes" in result
            
            if contains_hate:
                # Extract type
                type_match = re.search(r"TYPE: (.*?)(?:,|$)", result)
                hate_type = type_match.group(1) if type_match else "unknown"
                
                # Extract confidence
                confidence_match = re.search(r"CONFIDENCE: (.*?)(?:,|$)", result)
                confidence = confidence_match.group(1) if confidence_match else "Medium"
                
                # Extract explanation
                explanation_match = re.search(r"EXPLANATION: (.*?)(?:$)", result)
                explanation = explanation_match.group(1) if explanation_match else ""
                
                # Map to HateSpeechType
                mapped_type = None
                for hs_type in HateSpeechType:
                    if hs_type.value.lower() in hate_type.lower():
                        mapped_type = hs_type
                        break
                
                if not mapped_type:
                    # Default to the closest match or first type
                    mapped_type = HateSpeechType.DISCRIMINATION
                
                return (contains_hate, mapped_type, confidence, explanation)
            else:
                return (False, None, "High", "No hate speech detected")
                
        except Exception as e:
            print(f"Error using LLM for classification: {str(e)}")
            return (False, None, "Low", f"Error during analysis: {str(e)}")

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
        self.llm_classifier = HateSpeechClassifier()
        self.llm_analysis_result = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if message.content == self.HELP_KEYWORD:
            return ["This is the reporting system. Follow the prompts to report a message. You can say `cancel` at any time to cancel the report."]
        
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
            # If we have a message (either from reference or link), analyze it with LLM
            if self.message:
                # Analyze message content with LLM
                is_hate, hate_type, confidence, explanation = await self.llm_classifier.classify_message(self.message.content)
                self.llm_analysis_result = (is_hate, hate_type, confidence, explanation)
                
                # If hate speech was detected with high confidence
                if is_hate and confidence.lower() == "high":
                    self.reason = ReportReason.HATE_SPEECH
                    self.hate_speech_type = hate_type
                    self.state = State.AWAITING_CONFIRMATION
                    
                    return [
                        "I found this message:", 
                        "```" + self.message.author.name + ": " + self.message.content + "```",
                        f"Our AI analysis detected this as hate speech of type: {hate_type.value}",
                        f"Explanation: {explanation}",
                        "Is this correct? Please respond with 'yes' to confirm or 'no' to manually classify."
                    ]
                else:
                    # Proceed with normal flow if no hate speech detected or low confidence
                    self.state = State.AWAITING_REASON
                    reply = ["I found this message:", "```" + self.message.author.name + ": " + self.message.content + "```"]
                    
                    if is_hate:
                        reply.append(f"Our AI suggests this might contain {hate_type.value} (confidence: {confidence})")
                        reply.append(f"AI explanation: {explanation}")
                    
                    reply.extend([
                        "What is the reason for reporting this message? Please choose one of the following:", 
                        "1. hate speech", "2. spam", "3. violent and/or hateful entities", "4. violent speech", "5. other",
                        "\nPlease respond with the number or the exact text of your choice."
                    ])
                    return reply
        
        if self.state == State.AWAITING_CONFIRMATION:
            if message.content.lower() == 'yes':
                self.state = State.REPORT_COMPLETE
                return [
                    f"Thank you for your report. The message has been reported for: {self.reason.value} - {self.hate_speech_type.value}",
                    "Thank you for your report and we appreciate you helping to make our platform better and safer! We will thoroughly investigate your report shortly. In the meantime, please consider muting or blocking the reported account."
                ]
            elif message.content.lower() == 'no':
                self.state = State.AWAITING_REASON
                return [
                    "What is the reason for reporting this message? Please choose one of the following:", 
                    "1. hate speech", "2. spam", "3. violent and/or hateful entities", "4. violent speech", "5. other",
                    "\nPlease respond with the number or the exact text of your choice."
                ]
            else:
                return ["Please respond with 'yes' to confirm or 'no' to manually classify."]
        
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
                "Thank you for your report and we appreciate you helping to make our platform better and safer! We will thoroughly investigate your report shortly. In the meantime, please consider muting or blocking the reported account."
            ]

        return []

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE





