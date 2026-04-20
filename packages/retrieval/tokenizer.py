"""
Tokenizer for Chinese and English text.

Supports:
- Chinese tokenization using jieba
- English tokenization using simple splitting
- Stop words filtering
- Text normalization
"""

import re
from typing import List, Set
import jieba


class Tokenizer:
    """Tokenizer for mixed Chinese and English text."""

    # English stop words (common words to filter out)
    ENGLISH_STOP_WORDS = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'will', 'with', 'this', 'but', 'they', 'have', 'had',
        'what', 'when', 'where', 'who', 'which', 'why', 'how'
    }

    # Chinese stop words (common words to filter out)
    CHINESE_STOP_WORDS = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
        '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有',
        '看', '好', '自己', '这', '那', '里', '为', '与', '或', '等', '及'
    }

    def __init__(self, use_stop_words: bool = True):
        """
        Initialize tokenizer.

        Args:
            use_stop_words: Whether to filter out stop words
        """
        self.use_stop_words = use_stop_words
        self.stop_words = self.ENGLISH_STOP_WORDS | self.CHINESE_STOP_WORDS

        # Initialize jieba (silent mode)
        jieba.setLogLevel(jieba.logging.INFO)

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.

        Args:
            text: Input text (mixed Chinese and English)

        Returns:
            List of tokens
        """
        if not text:
            return []

        # Normalize text
        text = self._normalize(text)

        # Tokenize
        tokens = self._tokenize_mixed(text)

        # Filter stop words
        if self.use_stop_words:
            tokens = [t for t in tokens if t.lower() not in self.stop_words]

        return tokens

    def _normalize(self, text: str) -> str:
        """
        Normalize text.

        - Convert to lowercase for English
        - Remove extra whitespace
        - Keep Chinese characters as-is
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _tokenize_mixed(self, text: str) -> List[str]:
        """
        Tokenize mixed Chinese and English text.

        Strategy:
        1. Use jieba to tokenize (handles both Chinese and English)
        2. Further split English words if needed
        3. Filter out empty tokens
        """
        # Use jieba for initial tokenization
        tokens = jieba.lcut(text)

        # Post-process tokens
        result = []
        for token in tokens:
            token = token.strip()
            if not token:
                continue

            # If token is pure English, convert to lowercase
            if self._is_english(token):
                token = token.lower()

            result.append(token)

        return result

    def _is_english(self, text: str) -> bool:
        """Check if text is pure English (ASCII)."""
        return all(ord(c) < 128 for c in text)

    def _is_chinese(self, char: str) -> bool:
        """Check if character is Chinese."""
        return '\u4e00' <= char <= '\u9fff'

    def add_stop_words(self, words: Set[str]):
        """Add custom stop words."""
        self.stop_words.update(words)

    def remove_stop_words(self, words: Set[str]):
        """Remove stop words from the list."""
        self.stop_words -= words
