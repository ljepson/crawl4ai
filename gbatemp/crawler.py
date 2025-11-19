#!/usr/bin/env python3
"""
GBAtemp Forum Crawler
HTML extraction and HTTP-based crawling.
"""

import asyncio
import httpx
import re
from datetime import datetime, timezone
from typing import List, Optional
from bs4 import BeautifulSoup
from dateparser import parse as parse_date

from .parser import GBATempPost


class GBATempCrawler:
    """Crawls GBAtemp forum threads and extracts posts from HTML."""

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

                # Extract author (try multiple selectors)
                author_elem = article.find('span', itemprop='name')
                if not author_elem:
                    # Try alternate selector for thread starter posts
                    author_elem = article.find('h4', class_='message-name')
                    if author_elem:
                        author_elem = author_elem.find('a')
                if not author_elem:
                    # Try username class
                    author_elem = article.find('a', class_='username')

                author = author_elem.get_text(strip=True) if author_elem else 'Unknown'

                # Extract timestamp
                time_elem = article.find('time', class_='u-dt')
                timestamp = self.parse_timestamp(time_elem) if time_elem else None
                if not timestamp:
                    continue

                # Extract post number (look in the opposite/right side of header)
                # Try to find the link in message-attribution-opposite first
                post_num_link = article.find('ul', class_='message-attribution-opposite')
                post_number = None

                if post_num_link:
                    # Find all links and get the one with text starting with #
                    all_links = post_num_link.find_all('a', href=re.compile(r'/post-\d+'))
                    for link in all_links:
                        text = link.get_text(strip=True)
                        if text and text.startswith('#'):
                            post_number = text
                            break

                # Fallback methods if not found
                if not post_number:
                    # Try to find any link with post number pattern
                    post_num_link = article.find('a', href=re.compile(r'/post-\d+'))
                    if post_num_link:
                        text = post_num_link.get_text(strip=True)
                        if text:
                            # If text looks like a date, use post ID instead
                            if re.match(r'[A-Z][a-z]{2}\s+\d+,\s+\d{4}', text):
                                post_number = f"#{post_id}"
                            else:
                                post_number = text
                        else:
                            post_number = f"#{post_id}"
                    else:
                        post_number = f"#{post_id}"

                # Final fallback
                if not post_number:
                    post_number = f"#{post_id}"

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
                    after = after.replace(tzinfo=timezone.utc)
            filtered = [p for p in filtered if p.timestamp >= after]

        if before:
            # Make before timezone-aware if post timestamps are
            if posts and posts[0].timestamp and posts[0].timestamp.tzinfo:
                if not before.tzinfo:
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


class GBATempSimpleCrawler:
    """Crawls GBAtemp using HTTP requests (no browser needed)."""

    def __init__(self):
        self.crawler = GBATempCrawler()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def get_last_page_number(self, html: str) -> int:
        """
        Extract the last page number from thread HTML.
        Returns 1 if pagination not found.
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Look for pagination
        page_nav = soup.find('nav', class_='pageNav')
        if not page_nav:
            return 1

        # Find all page links
        page_links = page_nav.find_all('a', class_='pageNav-page')
        if not page_links:
            return 1

        # Get the highest page number
        max_page = 1
        for link in page_links:
            try:
                page_num = int(link.get_text(strip=True))
                max_page = max(max_page, page_num)
            except ValueError:
                continue

        return max_page

    async def fetch_thread(self, thread_url: str, max_pages: int = 1,
                          cutoff_date=None, reverse: bool = False) -> List[GBATempPost]:
        """
        Fetch posts from a GBAtemp thread using HTTP requests.

        Args:
            thread_url: URL of the thread
            max_pages: Maximum number of pages to crawl
            cutoff_date: Optional datetime - when reverse=True, stops crawling when posts older than this
            reverse: If True, crawl from last page backwards (useful with cutoff_date)

        Returns:
            List of extracted posts
        """
        all_posts = []

        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=30.0,
            follow_redirects=True,
            verify=False  # Ignore SSL errors
        ) as client:
            # Determine page range
            if reverse:
                # Use GBAtemp's redirect quirk: request page-9999 and it redirects to last page
                print(f"Detecting last page number...")

                # Build URL with impossibly high page number
                if '?' in thread_url:
                    probe_url = f"{thread_url}&page=9999"
                else:
                    base_url = thread_url.rstrip('/')
                    probe_url = f"{base_url}/page-9999"

                response = await client.get(probe_url)
                if response.status_code != 200:
                    print(f"  → Error: HTTP {response.status_code}")
                    return []

                # Parse last page number from redirected URL
                # URL format: .../page-439 or .../page-439?query
                url_match = re.search(r'/page-(\d+)', str(response.url))
                if url_match:
                    last_page = int(url_match.group(1))
                else:
                    # Fallback: parse from HTML if redirect didn't work
                    last_page = self.get_last_page_number(response.text)

                print(f"  → Found {last_page} pages (via redirect from page-9999)")

                # Extract posts from the redirected page (we already have the HTML!)
                html = response.text
                posts = self.crawler.extract_posts_from_html(html)

                if posts:
                    # If reverse crawling with cutoff_date, check for early stopping
                    if cutoff_date:
                        oldest_post = min(posts, key=lambda p: p.timestamp)
                        if oldest_post.timestamp < cutoff_date:
                            # Filter posts on this page
                            recent_posts = [p for p in posts if p.timestamp >= cutoff_date]
                            all_posts.extend(recent_posts)
                            print(f"  → Extracted {len(recent_posts)}/{len(posts)} posts from page {last_page} (hit date cutoff)")
                            # Stop early - no need to crawl further back
                            return all_posts

                    all_posts.extend(posts)
                    print(f"  → Extracted {len(posts)} posts from page {last_page}")

                # Crawl backwards from (last_page - 1) since we already processed last_page
                start_page = last_page - 1
                end_page = max(1, last_page - max_pages + 1)
                page_range = range(start_page, end_page - 1, -1)
            else:
                # Forward crawling (default)
                page_range = range(1, max_pages + 1)

            for page_num in page_range:
                try:
                    # Build URL with page number
                    if page_num == 1 and not reverse:
                        url = thread_url
                    else:
                        # Add page number to URL
                        if '?' in thread_url:
                            url = f"{thread_url}&page={page_num}"
                        else:
                            base_url = thread_url.rstrip('/')
                            url = f"{base_url}/page-{page_num}"

                    print(f"Fetching page {page_num}: {url}")

                    # Fetch page
                    response = await client.get(url)

                    if response.status_code != 200:
                        print(f"  → Error: HTTP {response.status_code}")
                        break

                    # Extract posts
                    html = response.text
                    posts = self.crawler.extract_posts_from_html(html)

                    if not posts:
                        print(f"  → No posts found (end of thread or page format changed)")
                        break

                    # If reverse crawling with cutoff_date, check for early stopping
                    if reverse and cutoff_date:
                        # Check if oldest post on this page is older than cutoff
                        oldest_post = min(posts, key=lambda p: p.timestamp)
                        if oldest_post.timestamp < cutoff_date:
                            # Filter posts on this page
                            recent_posts = [p for p in posts if p.timestamp >= cutoff_date]
                            all_posts.extend(recent_posts)
                            print(f"  → Extracted {len(recent_posts)}/{len(posts)} posts (hit date cutoff)")
                            print(f"  → Stopping: oldest post ({oldest_post.timestamp}) < cutoff ({cutoff_date})")
                            break

                    all_posts.extend(posts)
                    print(f"  → Extracted {len(posts)} posts")

                    # Small delay to be respectful
                    await asyncio.sleep(1)

                except Exception as e:
                    print(f"  → Error fetching page {page_num}: {e}")
                    break

        return all_posts
