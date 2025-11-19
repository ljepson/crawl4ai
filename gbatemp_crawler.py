#!/usr/bin/env python3
"""
GBAtemp Switch Forum Crawler
Crawls posts from GBAtemp, filters by date and relevance.
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from dateparser import parse as parse_date


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


class GBATempCrawler:
    """Crawls GBAtemp forum threads and extracts posts."""

    def __init__(self):
        self.base_url = "https://gbatemp.net"

    def parse_timestamp(self, time_element) -> Optional[datetime]:
        """
        Parse timestamp from HTML time element.
        Handles both ISO 8601 and relative times.
        """
        try:
            # Try ISO 8601 format first (most reliable)
            iso_time = time_element.get('datetime')
            if iso_time:
                return datetime.fromisoformat(iso_time.replace('Z', '+00:00'))

            # Fallback to unix timestamp
            unix_timestamp = time_element.get('data-timestamp')
            if unix_timestamp:
                return datetime.fromtimestamp(int(unix_timestamp))

            # Fallback to text parsing (least reliable)
            time_text = time_element.get_text(strip=True)
            return parse_date(time_text)

        except Exception as e:
            print(f"Warning: Could not parse timestamp: {e}")
            return None

    def extract_posts_from_html(self, html: str) -> List[GBATempPost]:
        """
        Extract all posts from a thread page HTML.
        """
        soup = BeautifulSoup(html, 'html.parser')
        posts = []

        # Find all post articles
        post_articles = soup.find_all('article', class_='message--post')

        for article in post_articles:
            try:
                # Extract post ID
                post_id = article.get('data-content', '').replace('post-', '')
                if not post_id:
                    continue

                # Extract author
                author_elem = article.find('span', itemprop='name')
                author = author_elem.get_text(strip=True) if author_elem else 'Unknown'

                # Extract timestamp
                time_elem = article.find('time', class_='u-dt')
                timestamp = self.parse_timestamp(time_elem) if time_elem else None
                if not timestamp:
                    continue

                # Extract post number
                post_num_link = article.find('a', href=re.compile(r'/post-\d+'))
                post_number = post_num_link.get_text(strip=True) if post_num_link else '?'

                # Extract content
                content_div = article.find('div', class_='bbWrapper')
                if content_div:
                    # Remove quoted content to get only new content
                    for quote in content_div.find_all('blockquote'):
                        quote.decompose()
                    content = content_div.get_text('\n', strip=True)
                else:
                    content = ''

                # Extract attachments
                attachments = []
                attachment_section = article.find('section', class_='message-attachments')
                if attachment_section:
                    for attachment_li in attachment_section.find_all('li', class_='file'):
                        file_name_span = attachment_li.find('span', class_='file-name')
                        file_meta_div = attachment_li.find('div', class_='file-meta')
                        file_link = attachment_li.find('a', class_='file-preview')

                        if file_name_span:
                            att_info = {
                                'name': file_name_span.get('title') or file_name_span.get_text(strip=True),
                                'size': file_meta_div.get_text(strip=True).split('·')[0].strip() if file_meta_div else '?',
                                'url': self.base_url + file_link.get('href') if file_link else ''
                            }
                            attachments.append(att_info)

                # Extract reactions
                reactions = 0
                reactions_bar = article.find('div', class_='reactionsBar')
                if reactions_bar:
                    reaction_links = reactions_bar.find_all('a', class_='reactionsBar-link')
                    reactions = len(reaction_links)

                # Build post URL
                post_url = f"{self.base_url}/threads/_.{post_id.split('-')[0]}/post-{post_id}"

                # Create post object
                post = GBATempPost(
                    post_id=post_id,
                    author=author,
                    timestamp=timestamp,
                    content=content,
                    post_number=post_number,
                    url=post_url,
                    attachments=attachments,
                    reactions=reactions
                )

                posts.append(post)

            except Exception as e:
                print(f"Warning: Failed to parse post: {e}")
                continue

        return posts

    def filter_posts_by_date(self, posts: List[GBATempPost],
                            after: Optional[datetime] = None,
                            before: Optional[datetime] = None) -> List[GBATempPost]:
        """Filter posts by date range."""
        filtered = posts

        if after:
            # Make after timezone-aware if post timestamps are
            if posts and posts[0].timestamp and posts[0].timestamp.tzinfo:
                if not after.tzinfo:
                    from datetime import timezone
                    after = after.replace(tzinfo=timezone.utc)
            filtered = [p for p in filtered if p.timestamp >= after]

        if before:
            # Make before timezone-aware if post timestamps are
            if posts and posts[0].timestamp and posts[0].timestamp.tzinfo:
                if not before.tzinfo:
                    from datetime import timezone
                    before = before.replace(tzinfo=timezone.utc)
            filtered = [p for p in filtered if p.timestamp <= before]

        return filtered

    def filter_posts_by_relevance(self, posts: List[GBATempPost],
                                  min_score: float = 20.0) -> List[GBATempPost]:
        """
        Filter posts by relevance score.
        Calculates relevance for each post and filters by minimum score.
        """
        for post in posts:
            post.calculate_relevance()

        return [p for p in posts if p.relevance_score >= min_score]


# Example usage
async def main():
    """
    Example: Extract posts from provided HTML samples.
    """

    # Read the HTML samples provided by user
    relevant_html = '''<article class="message   message--post   js-post js-inlineModContainer   " data-author="bth" data-content="post-10769525" id="js-post-10769525">
        <time class="u-dt" datetime="2025-11-19T17:07:04+0000" data-timestamp="1763572024">Today at 5:07 PM</time>
        <span itemprop="name">bth</span>
        <div class="bbWrapper">
            your question fails to understand why there should be a patch.
            the same reason the nim patch exists...
            from 0x84F44, a9 c3 5f 38 - ldurb w9, [x29, #-4]
            to: 0x84F44, e9 03 1f 2a - mov w9, wzr
        </div>
        <section class="message-attachments">
            <li class="file">
                <span class="file-name" title="atmosphere.zip">atmosphere.zip</span>
                <div class="file-meta">1.1 KB</div>
            </li>
        </section>
    </article>'''

    irrelevant_html = '''<article class="message   message--post   js-post js-inlineModContainer   " data-author="josete2k" data-content="post-10769529" id="js-post-10769529">
        <time class="u-dt" datetime="2025-11-19T17:10:16+0000" data-timestamp="1763572216">Today at 5:10 PM</time>
        <span itemprop="name">josete2k</span>
        <div class="bbWrapper">
            I see... Just one Last question.
            Do we need a fake linked account with your patch?
            I'll give a try tonight
        </div>
    </article>'''

    crawler = GBATempCrawler()

    # Parse posts
    print("Extracting posts from HTML samples...")
    relevant_posts = crawler.extract_posts_from_html(relevant_html)
    irrelevant_posts = crawler.extract_posts_from_html(irrelevant_html)

    all_posts = relevant_posts + irrelevant_posts

    # Calculate relevance scores
    print("\n=== RELEVANCE ANALYSIS ===\n")
    for post in all_posts:
        post.calculate_relevance()
        print(f"Post #{post.post_number} by {post.author}")
        print(f"Timestamp: {post.timestamp}")
        print(f"Content length: {len(post.content)} chars")
        print(f"Attachments: {len(post.attachments)}")
        print(f"Relevance Score: {post.relevance_score:.1f}/100")
        print(f"Content preview: {post.content[:100]}...")
        print(f"{'✓ RELEVANT' if post.relevance_score >= 20 else '✗ IRRELEVANT'}")
        print("-" * 60)

    # Filter by relevance (min score 20)
    relevant_filtered = crawler.filter_posts_by_relevance(all_posts, min_score=20)

    print(f"\n=== FILTERING RESULTS ===")
    print(f"Total posts: {len(all_posts)}")
    print(f"Relevant posts (score >= 20): {len(relevant_filtered)}")
    print(f"Filtered out: {len(all_posts) - len(relevant_filtered)}")

    # Export to JSON
    output = {
        'crawl_date': datetime.now().isoformat(),
        'total_posts': len(all_posts),
        'relevant_posts': len(relevant_filtered),
        'posts': [p.to_dict() for p in relevant_filtered]
    }

    with open('gbatemp_filtered_posts.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: gbatemp_filtered_posts.json")


if __name__ == '__main__':
    asyncio.run(main())
