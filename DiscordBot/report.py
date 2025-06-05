from enum import Enum, auto
import discord
import re
import openai
import os

class State(Enum):
    REPORT_START = auto()
    AWAITING_IMMEDIATE_THREAT_CHECK = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_REASON = auto()
    AWAITING_SLUR_TYPE = auto()
    AWAITING_TARGET_GROUP = auto()
    AWAITING_CONTEXT = auto()
    AWAITING_ADDITIONAL_CONTEXT_PROMPT = auto()
    AWAITING_ADDITIONAL_CONTEXT = auto()
    REPORT_COMPLETE = auto()
    AWAITING_CONFIRMATION = auto()

class ReportReason(Enum):
    SLURS = "slurs"
    SPAM = "spam"
    SEXUAL_CONTENT = "sexual content"
    DISCRIMINATION = "discrimination"
    HARASSMENT = "harassment"
    OTHER = "other"

class SlurType(Enum):
    RACE = "race"
    ETHNICITY = "ethnicity"
    GENDER = "gender"
    DISABILITY = "disability"
    SEXUAL_ORIENTATION = "sexual orientation"

class TargetGroup(Enum):
    INDIVIDUAL = "individual"
    GROUP = "group"
    SELF_REFERENCE = "self reference"

class Context(Enum):
    JOKE = "joke"
    DIRECT_ATTACK = "direct attack"
    QUOTE = "quote"
    DISCUSSION = "discussion"

class HateSpeechClassifier:
    def __init__(self):
        openai.api_key = os.environ.get("OPENAI_API_KEY")
    
    async def classify_message(self, message_content):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an AI trained to detect and classify hate speech in messages."},
                    {"role": "user", "content": f"Analyze this message for hate speech: '{message_content}'. If it contains hate speech, specify the type (slurs, sexual content, discrimination, harassment, other) and provide a brief explanation. Format your response as: CONTAINS_HATE_SPEECH: [Yes/No], TYPE: [type if applicable], CONFIDENCE: [High/Medium/Low], EXPLANATION: [brief explanation]"}
                ]
            )
            result = response.choices[0].message.content
            contains_hate = "CONTAINS_HATE_SPEECH: Yes" in result
            if contains_hate:
                type_match = re.search(r"TYPE: (.*?)(?:,|$)", result)
                hate_type = type_match.group(1).strip().lower() if type_match else "unknown"
                confidence_match = re.search(r"CONFIDENCE: (.*?)(?:,|$)", result)
                confidence = confidence_match.group(1) if confidence_match else "Medium"
                explanation_match = re.search(r"EXPLANATION: (.*?)(?:$)", result)
                explanation = explanation_match.group(1) if explanation_match else ""
                # Map to ReportReason
                mapped_type = None
                for rtype in ReportReason:
                    if rtype.value in hate_type:
                        mapped_type = rtype
                        break
                if not mapped_type:
                    mapped_type = ReportReason.OTHER
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
        self.slur_type = None
        self.target_group = None
        self.context = None
        self.additional_context = None
        self.is_immediate_threat = False
        self.llm_classifier = HateSpeechClassifier()
        self.llm_analysis_result = None

    async def handle_message(self, message):
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        if message.content == self.HELP_KEYWORD:
            return ["This is the reporting system. Follow the prompts to report a message. You can say `cancel` at any time to cancel the report."]

        # IMMEDIATE THREAT CHECK
        if self.state == State.REPORT_START:
            self.state = State.AWAITING_IMMEDIATE_THREAT_CHECK
            return ["Is this an immediate threat requiring URGENT moderator attention? (yes/no)"]

        if self.state == State.AWAITING_IMMEDIATE_THREAT_CHECK:
            response = message.content.strip().lower()
            if response in ['yes', 'y']:
                self.is_immediate_threat = True
            elif response in ['no', 'n']:
                self.is_immediate_threat = False
            else:
                return ["Please respond with 'yes' or 'no'."]
            reply = "Thank you for starting the reporting process.\n\nPlease copy paste the link to the message you want to report.\nYou can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]

        if self.state == State.AWAITING_MESSAGE:
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
            if self.message:
                is_hate, hate_type, confidence, explanation = await self.llm_classifier.classify_message(self.message.content)
                self.llm_analysis_result = (is_hate, hate_type, confidence, explanation)
                reply = [
                    "I found this message:",
                    f"``````"
                ]
                if is_hate:
                    reply.append(f"Our AI suggests this might contain {hate_type.value} (confidence: {confidence})")
                    reply.append(f"AI explanation: {explanation}")
                reply.extend([
                    "What is the reason for reporting this message? Please choose one of the following:",
                    "1. slurs", "2. spam", "3. sexual content", "4. discrimination", "5. harassment", "6. other",
                    "\nPlease respond with the number or the exact text of your choice."
                ])
                self.state = State.AWAITING_REASON
                return reply

        if self.state == State.AWAITING_REASON:
            reason_text = message.content.strip().lower()
            if reason_text in ["1", "slurs"]:
                self.reason = ReportReason.SLURS
                self.state = State.AWAITING_SLUR_TYPE
                return [
                    "Please specify the type of slur. Choose one of the following:",
                    "1. race", "2. ethnicity", "3. gender", "4. disability", "5. sexual orientation",
                    "\nPlease respond with the number or the exact text of your choice."
                ]
            elif reason_text in ["2", "spam"]:
                self.reason = ReportReason.SPAM
            elif reason_text in ["3", "sexual content"]:
                self.reason = ReportReason.SEXUAL_CONTENT
            elif reason_text in ["4", "discrimination"]:
                self.reason = ReportReason.DISCRIMINATION
            elif reason_text in ["5", "harassment"]:
                self.reason = ReportReason.HARASSMENT
            elif reason_text in ["6", "other"]:
                self.reason = ReportReason.OTHER
            else:
                return ["Please choose a valid reason by entering either the number (1-6) or the exact text of one of the options above."]
            if self.reason == ReportReason.SLURS:
                pass
            else:
                self.state = State.AWAITING_ADDITIONAL_CONTEXT_PROMPT
                return [
                    "Would you like to provide any additional context or information for the moderators? (yes/no)"
                ]

        if self.state == State.AWAITING_SLUR_TYPE:
            type_text = message.content.strip().lower()
            if type_text in ["1", "race"]:
                self.slur_type = SlurType.RACE
            elif type_text in ["2", "ethnicity"]:
                self.slur_type = SlurType.ETHNICITY
            elif type_text in ["3", "gender"]:
                self.slur_type = SlurType.GENDER
            elif type_text in ["4", "disability"]:
                self.slur_type = SlurType.DISABILITY
            elif type_text in ["5", "sexual orientation"]:
                self.slur_type = SlurType.SEXUAL_ORIENTATION
            else:
                return ["Please choose a valid slur type by entering either the number (1-5) or the exact text of one of the options above."]
            self.state = State.AWAITING_TARGET_GROUP
            return [
                "Who is being targeted?",
                "1. individual", "2. group", "3. self reference",
                "\nPlease respond with the number or the exact text of your choice."
            ]

        if self.state == State.AWAITING_TARGET_GROUP:
            group_text = message.content.strip().lower()
            if group_text in ["1", "individual"]:
                self.target_group = TargetGroup.INDIVIDUAL
            elif group_text in ["2", "group"]:
                self.target_group = TargetGroup.GROUP
            elif group_text in ["3", "self reference"]:
                self.target_group = TargetGroup.SELF_REFERENCE
            else:
                return ["Please choose a valid target group by entering either the number (1-3) or the exact text of one of the options above."]
            self.state = State.AWAITING_CONTEXT
            return [
                "What is the context?",
                "1. joke", "2. direct attack", "3. quote", "4. discussion",
                "\nPlease respond with the number or the exact text of your choice."
            ]

        if self.state == State.AWAITING_CONTEXT:
            context_text = message.content.strip().lower()
            if context_text in ["1", "joke"]:
                self.context = Context.JOKE
            elif context_text in ["2", "direct attack"]:
                self.context = Context.DIRECT_ATTACK
            elif context_text in ["3", "quote"]:
                self.context = Context.QUOTE
            elif context_text in ["4", "discussion"]:
                self.context = Context.DISCUSSION
            else:
                return ["Please choose a valid context by entering either the number (1-4) or the exact text of one of the options above."]
            self.state = State.AWAITING_ADDITIONAL_CONTEXT_PROMPT
            return [
                "Would you like to provide any additional context or information for the moderators? (yes/no)"
            ]

        if self.state == State.AWAITING_ADDITIONAL_CONTEXT_PROMPT:
            if message.content.strip().lower() in ["yes", "y"]:
                self.state = State.AWAITING_ADDITIONAL_CONTEXT
                return ["Please type any additional context you'd like to provide. If you have nothing to add, type 'skip'."]
            elif message.content.strip().lower() in ["no", "n", "skip"]:
                self.additional_context = None
                self.state = State.REPORT_COMPLETE
                return self._report_summary()
            else:
                return ["Please respond with 'yes' or 'no'."]

        if self.state == State.AWAITING_ADDITIONAL_CONTEXT:
            if message.content.strip().lower() == "skip":
                self.additional_context = None
            else:
                self.additional_context = message.content
            self.state = State.REPORT_COMPLETE
            return self._report_summary()

        return []

    def _report_summary(self):
        summary = [
            "Thank you for your report. Here is a summary:",
            f"- Immediate threat: {'YES' if self.is_immediate_threat else 'No'}",
            f"- Reason: {self.reason.value}"
        ]
        if self.reason == ReportReason.SLURS:
            summary.extend([
                f"- Slur Type: {self.slur_type.value}",
                f"- Target Group: {self.target_group.value}",
                f"- Context: {self.context.value}"
            ])
        if self.additional_context:
            summary.append(f"- Additional context: {self.additional_context}")
        summary.append("We appreciate your help in keeping our platform safe. The moderation team will review your report shortly.")
        return summary

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
