import os
import re
import csv
import json
import openai
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

# Load tokens from tokens.json
with open(os.path.join(os.path.dirname(__file__), "tokens.json")) as f:
    tokens = json.load(f)
openai_api_key = tokens.get("openai")
perspective_api_key = tokens.get("perspective_api_key")

class DetectionMethod(Enum):
    PERSPECTIVE_API = "perspective_api"
    OPENAI_API = "openai_api"
    REGEX_SLURS = "regex_slurs"

@dataclass
class DetectionResult:
    method: DetectionMethod
    is_hate_speech: bool
    confidence: float
    category: Optional[str] = None
    explanation: Optional[str] = None
    detected_terms: Optional[List[str]] = None

class HateSpeechDetector:
    def __init__(self):
        self.openai_api_key = openai_api_key
        self.perspective_api_key = perspective_api_key
        self.slurs = self._load_slurs()

    def _load_slurs(self) -> set:
        slurs = set()
        try:
            with open(os.path.join(os.path.dirname(__file__), 'data/list-of-swearwords-and-offensive-gestures.csv'), 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    slurs.add(row['Word'].lower())
                    if row['Alternative spellings']:
                        for alt in row['Alternative spellings'].split(','):
                            slurs.add(alt.strip().lower())
        except Exception as e:
            print(f"Error loading slurs: {e}")
        return slurs

    async def detect_with_perspective_api(self, text: str) -> DetectionResult:
        if not self.perspective_api_key:
            return DetectionResult(
                method=DetectionMethod.PERSPECTIVE_API,
                is_hate_speech=False,
                confidence=0.0,
                explanation="Perspective API key not configured"
            )
        try:
            import aiohttp
            url = f"https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key={self.perspective_api_key}"
            headers = {"Content-Type": "application/json"}
            data = {
                "comment": {"text": text},
                "languages": ["en"],
                "requestedAttributes": {
                    "TOXICITY": {},
                    "SEVERE_TOXICITY": {},
                    "IDENTITY_ATTACK": {},
                    "INSULT": {},
                    "PROFANITY": {},
                    "THREAT": {}
                },
                "doNotStore": True
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    result = await resp.json()
                    if "attributeScores" not in result:
                        return DetectionResult(
                            method=DetectionMethod.PERSPECTIVE_API,
                            is_hate_speech=False,
                            confidence=0.0,
                            explanation=f"Unexpected API response: {result}"
                        )
                    # Get the highest toxicity score
                    scores = []
                    for attr in result["attributeScores"]:
                        scores.append(result["attributeScores"][attr]["summaryScore"]["value"])
                    score = max(scores) if scores else 0.0
                    is_hate = score > 0.7
                    return DetectionResult(
                        method=DetectionMethod.PERSPECTIVE_API,
                        is_hate_speech=is_hate,
                        confidence=score,
                        category="TOXICITY" if is_hate else None,
                        explanation=f"Perspective API highest toxicity score: {score:.2f}"
                    )
        except Exception as e:
            return DetectionResult(
                method=DetectionMethod.PERSPECTIVE_API,
                is_hate_speech=False,
                confidence=0.0,
                explanation=f"Error calling Perspective API: {str(e)}"
            )

    async def detect_with_openai_api(self, text: str) -> DetectionResult:
        if not self.openai_api_key:
            return DetectionResult(
                method=DetectionMethod.OPENAI_API,
                is_hate_speech=False,
                confidence=0.0,
                explanation="OpenAI API key not configured"
            )
        try:
            client = openai.OpenAI(api_key=self.openai_api_key)
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
            result = json.loads(response.choices[0].message.content)
            return DetectionResult(
                method=DetectionMethod.OPENAI_API,
                is_hate_speech=result.get('hate_speech_detected', False),
                confidence=result.get('confidence_score', 0.0),
                category=result.get('category'),
                explanation=result.get('explanation')
            )
        except Exception as e:
            return DetectionResult(
                method=DetectionMethod.OPENAI_API,
                is_hate_speech=False,
                confidence=0.0,
                explanation=f"Error calling OpenAI API: {str(e)}"
            )

    def detect_with_regex_slurs(self, text: str) -> DetectionResult:
        text_lower = text.lower()
        detected_terms = []
        for slur in self.slurs:
            if slur and slur in text_lower:
                detected_terms.append(slur)
        return DetectionResult(
            method=DetectionMethod.REGEX_SLURS,
            is_hate_speech=len(detected_terms) > 0,
            confidence=1.0 if detected_terms else 0.0,
            category="slurs" if detected_terms else None,
            explanation=f"Found {len(detected_terms)} potential slurs" if detected_terms else "No slurs detected",
            detected_terms=detected_terms
        )

    async def detect_with_combined_methods(self, text: str, methods: List[DetectionMethod]) -> List[DetectionResult]:
        results = []
        for method in methods:
            if method == DetectionMethod.PERSPECTIVE_API:
                result = await self.detect_with_perspective_api(text)
            elif method == DetectionMethod.OPENAI_API:
                result = await self.detect_with_openai_api(text)
            elif method == DetectionMethod.REGEX_SLURS:
                result = self.detect_with_regex_slurs(text)
            else:
                continue
            results.append(result)
        return results

    def evaluate_results(self, results: List[DetectionResult]) -> Dict:
        hate_speech_count = sum(1 for r in results if r.is_hate_speech)
        avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0
        all_terms = []
        for r in results:
            if r.detected_terms:
                all_terms.extend(r.detected_terms)
        categories = [r.category for r in results if r.category]
        explanations = [r.explanation for r in results if r.explanation]
        return {
            "is_hate_speech": hate_speech_count > 0,
            "confidence": avg_confidence,
            "detection_count": hate_speech_count,
            "total_methods": len(results),
            "categories": list(set(categories)),
            "detected_terms": list(set(all_terms)),
            "explanations": explanations,
            "method_results": [r.__dict__ for r in results]
        } 