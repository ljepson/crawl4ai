#!/usr/bin/env python3
"""
GBAtemp Post Parser
Defines the GBATempPost class with relevance scoring.
"""

import re
from datetime import datetime
from typing import List, Dict


class GBATempPost:
    """Represents a single forum post."""

    def __init__(self, post_id: str, author: str, timestamp: datetime,
                 content: str, post_number: str, url: str,
                 attachments: List[Dict] = None, reactions: int = 0):
        self.post_id = post_id
        self.author = author
        self.timestamp = timestamp
        self.content = content
        self.post_number = post_number
        self.url = url
        self.attachments = attachments or []
        self.reactions = reactions
        self.relevance_score = 0.0

    def calculate_relevance(self) -> float:
        """
        Calculate relevance score based on multiple factors.
        Returns score 0-100 (higher = more relevant).
        """
        score = 0.0

        # 1. Content length (0-20 points)
        content_len = len(self.content)
        if content_len > 500:
            score += 20
        elif content_len > 300:
            score += 15
        elif content_len > 150:
            score += 10
        elif content_len > 75:
            score += 5
        else:
            score += 0  # Too short

        # 2. Has code blocks or hex values (0-25 points)
        # Detect hex patterns like: 0x84F44, a9 c3 5f 38
        hex_pattern = r'0x[0-9a-fA-F]{4,}|[0-9a-fA-F]{2}\s+[0-9a-fA-F]{2}'
        if re.search(hex_pattern, self.content):
            score += 25

        # Detect code-like content (C, Python, assembly)
        code_indicators = [
            r'```',  # Markdown code block
            r'\bvoid\s+\w+\s*\(',  # C function
            r'\bint\s+\w+\s*=',  # Variable declaration
            r'mov\s+\w+,',  # Assembly
            r'ldurb\s+\w+,',  # ARM instruction
        ]
        if any(re.search(pattern, self.content) for pattern in code_indicators):
            score += 15

        # 3. Has attachments (0-20 points)
        if self.attachments:
            score += 10
            # Bonus for relevant file types
            relevant_extensions = ['.zip', '.nro', '.kip', '.nsp', '.xci', '.ips']
            for attachment in self.attachments:
                filename = attachment.get('name', '').lower()
                if any(filename.endswith(ext) for ext in relevant_extensions):
                    score += 10
                    break

        # 4. Has version numbers (0-15 points)
        # Pattern: 1.0.0, v2.5.1, version 3.0
        version_pattern = r'\b(?:v|version\s+)?(\d+)\.(\d+)(?:\.(\d+))?'
        if re.search(version_pattern, self.content, re.IGNORECASE):
            score += 15

        # 5. Technical keywords (0-10 points)
        tech_keywords = [
            'atmosphere', 'firmware', 'patch', 'sysmodule', 'homebrew',
            'fusee', 'hekate', 'tinfoil', 'goldleaf', 'edizon',
            'sys-patch', 'sigpatches', 'exosphere', 'stratosphere'
        ]
        keyword_count = sum(1 for kw in tech_keywords
                           if kw.lower() in self.content.lower())
        score += min(keyword_count * 2, 10)

        # 6. Has reactions/engagement (0-5 points)
        if self.reactions > 0:
            score += min(self.reactions * 2, 5)

        # 7. Penalty for question-only posts (-30 points)
        # Short posts ending with "?" are likely just questions
        if content_len < 150 and self.content.strip().endswith('?'):
            score -= 30

        # Extra penalty if very short question (stacks with above)
        if content_len < 150 and '?' in self.content:
            score -= 20

        # Penalty for posts that are mostly questions
        question_ratio = self.content.count('?') / max(1, len(self.content.split('.')))
        if question_ratio > 0.5:
            score -= 15

        # 8. Penalty for generic responses (-15 points)
        generic_phrases = [
            r'^thanks?!*$',
            r'^thank you!*$',
            r'^me too!*$',
            r'^same here!*$',
            r'^works for me!*$',
            r'^\+1$',
        ]
        content_lower = self.content.lower().strip()
        if any(re.match(pattern, content_lower) for pattern in generic_phrases):
            score -= 15

        self.relevance_score = max(0, min(100, score))
        return self.relevance_score

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'post_id': self.post_id,
            'post_number': self.post_number,
            'author': self.author,
            'timestamp': self.timestamp.isoformat(),
            'url': self.url,
            'content': self.content,
            'attachments': self.attachments,
            'reactions': self.reactions,
            'relevance_score': self.relevance_score,
        }
