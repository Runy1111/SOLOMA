"""
Agent 4: Spam Detector
Detects spam by comparing new messages with recent message history
"""
from typing import List, Tuple
from collections import deque
from difflib import SequenceMatcher
from gigachat_client import GigachatClient
from config.settings import GIGACHAT_CLIENT_ID, GIGACHAT_AUTH_KEY, GIGACHAT_SCOPE, SPAM_SIMILARITY_THRESHOLD, MESSAGE_HISTORY_SIZE


class SpamDetectionResult:
    def __init__(self, is_spam: bool, similarity_score: float = 0.0, similar_message: str = ""):
        self.is_spam = is_spam
        self.similarity_score = similarity_score  # 0.0 to 1.0
        self.similar_message = similar_message  # Which message was similar


class SpamDetectorAgent:
    def __init__(self, history_size: int = MESSAGE_HISTORY_SIZE):
        self.history: deque = deque(maxlen=history_size)
        self.client = GigachatClient(
            client_id=GIGACHAT_CLIENT_ID,
            auth_key=GIGACHAT_AUTH_KEY,
            scope=GIGACHAT_SCOPE
        )
        self.similarity_threshold = SPAM_SIMILARITY_THRESHOLD

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (0.0 to 1.0)"""
        # Simple ratio calculation
        ratio = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        return ratio

    def add_message(self, message: str, user_id: int = None):
        """Add message to history"""
        self.history.append({
            "text": message,
            "user_id": user_id
        })

    async def check_spam(self, message: str, user_id: int = None) -> SpamDetectionResult:
        """
        Check if new message is spam by comparing with history
        Returns SpamDetectionResult
        """
        try:
            max_similarity = 0.0
            similar_msg = ""

            # Check against all messages in history
            for old_msg in self.history:
                similarity = self._calculate_similarity(message, old_msg["text"])
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    similar_msg = old_msg["text"]

            # Consider it spam if similarity is above threshold
            is_spam = max_similarity >= self.similarity_threshold

            return SpamDetectionResult(
                is_spam=is_spam,
                similarity_score=max_similarity,
                similar_message=similar_msg if is_spam else ""
            )

        except Exception as e:
            print(f"Error in SpamDetectorAgent.check_spam: {e}")
            return SpamDetectionResult(is_spam=False, similarity_score=0.0)

    async def close(self):
        await self.client.close()
