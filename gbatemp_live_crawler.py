#!/usr/bin/env python3
"""
Live GBAtemp Crawler - Fetches posts from live forum pages.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Optional
from playwright.async_api import async_playwright
from gbatemp_crawler import GBATempCrawler, GBATempPost


class GBATempLiveCrawler:
    """Crawls live GBAtemp forum pages using Playwright."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.crawler = GBATempCrawler()

    async def fetch_thread(self, thread_url: str, max_pages: int = 1) -> List[GBATempPost]:
        """
        Fetch posts from a GBAtemp thread.

        Args:
            thread_url: URL of the thread (e.g., https://gbatemp.net/threads/sys-patch.633517/)
            max_pages: Maximum number of pages to crawl (default: 1)

        Returns:
            List of extracted posts
        """
        all_posts = []

        async with async_playwright() as p:
            # Launch browser (disable sandbox for container environments)
            browser = await p.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                ignore_https_errors=True
            )
            page = await context.new_page()

            try:
                # Fetch first page
                print(f"Fetching: {thread_url}")
                await page.goto(thread_url, wait_until='domcontentloaded', timeout=60000)

                # Wait a bit for dynamic content
                await asyncio.sleep(2)

                # Wait for posts to load (increased timeout)
                try:
                    await page.wait_for_selector('article.message--post', timeout=20000)
                except Exception as e:
                    # Debug: save screenshot and HTML
                    await page.screenshot(path='debug_screenshot.png')
                    html = await page.content()
                    with open('debug_page.html', 'w') as f:
                        f.write(html)
                    print(f"  → Could not find posts. Saved debug_screenshot.png and debug_page.html")
                    raise

                # Extract posts from first page
                html = await page.content()
                posts = self.crawler.extract_posts_from_html(html)
                all_posts.extend(posts)
                print(f"  → Extracted {len(posts)} posts from page 1")

                # Check for pagination
                if max_pages > 1:
                    for page_num in range(2, max_pages + 1):
                        # Look for next page link
                        next_button = await page.query_selector('a.pageNav-jump--next')
                        if not next_button:
                            print(f"  → No more pages found")
                            break

                        # Click next page
                        print(f"Fetching page {page_num}...")
                        await next_button.click()
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_selector('article.message--post', timeout=10000)

                        # Extract posts
                        html = await page.content()
                        posts = self.crawler.extract_posts_from_html(html)
                        all_posts.extend(posts)
                        print(f"  → Extracted {len(posts)} posts from page {page_num}")

            except Exception as e:
                print(f"Error fetching thread: {e}")

            finally:
                await context.close()
                await browser.close()

        return all_posts

    async def fetch_forum_threads(self, forum_url: str = "https://gbatemp.net/forums/nintendo-switch.283/",
                                  max_threads: int = 10) -> List[dict]:
        """
        Fetch recent threads from a forum listing page.

        Args:
            forum_url: URL of the forum (e.g., https://gbatemp.net/forums/nintendo-switch.283/)
            max_threads: Maximum number of threads to extract

        Returns:
            List of thread info dicts with: title, url, author, last_post_time, reply_count
        """
        threads = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                ignore_https_errors=True
            )
            page = await context.new_page()

            try:
                print(f"Fetching forum page: {forum_url}")
                await page.goto(forum_url, wait_until='domcontentloaded', timeout=30000)

                # Wait for thread listings
                await page.wait_for_selector('.structItem-title', timeout=10000)

                # Extract thread information
                thread_elements = await page.query_selector_all('.structItem--thread')

                for i, elem in enumerate(thread_elements[:max_threads]):
                    try:
                        # Extract title and URL
                        title_elem = await elem.query_selector('.structItem-title a')
                        title = await title_elem.inner_text() if title_elem else '?'
                        thread_url = await title_elem.get_attribute('href') if title_elem else None
                        if thread_url and not thread_url.startswith('http'):
                            thread_url = f"https://gbatemp.net{thread_url}"

                        # Extract author
                        author_elem = await elem.query_selector('.username')
                        author = await author_elem.inner_text() if author_elem else '?'

                        # Extract last post time
                        time_elem = await elem.query_selector('time')
                        last_post_time = await time_elem.get_attribute('datetime') if time_elem else None

                        # Extract reply count
                        replies_elem = await elem.query_selector('.structItem-cell--meta dd')
                        replies = await replies_elem.inner_text() if replies_elem else '0'

                        thread_info = {
                            'title': title.strip(),
                            'url': thread_url,
                            'author': author.strip(),
                            'last_post_time': last_post_time,
                            'replies': replies.strip()
                        }

                        threads.append(thread_info)

                    except Exception as e:
                        print(f"Warning: Failed to extract thread {i+1}: {e}")
                        continue

                print(f"  → Extracted {len(threads)} threads")

            except Exception as e:
                print(f"Error fetching forum page: {e}")

            finally:
                await context.close()
                await browser.close()

        return threads


async def main():
    """
    Example usage: Crawl GBAtemp Switch forum
    """
    import argparse

    parser = argparse.ArgumentParser(description='GBAtemp Forum Crawler')
    parser.add_argument('--url', type=str,
                       default='https://gbatemp.net/threads/sys-patch-sysmod-that-patches-on-boot.633517/',
                       help='Thread URL to crawl')
    parser.add_argument('--pages', type=int, default=1,
                       help='Maximum pages to crawl')
    parser.add_argument('--min-score', type=float, default=20.0,
                       help='Minimum relevance score (0-100)')
    parser.add_argument('--since', type=str, default=None,
                       help='Filter posts after this date (e.g., "2025-11-19" or "2 hours ago")')
    parser.add_argument('--output', type=str, default='gbatemp_results.json',
                       help='Output JSON file')
    parser.add_argument('--show-browser', action='store_true',
                       help='Show browser window (not headless)')

    args = parser.parse_args()

    # Create crawler
    live_crawler = GBATempLiveCrawler(headless=not args.show_browser)

    # Fetch posts
    print(f"\n{'='*70}")
    print("GBATEMP LIVE CRAWLER")
    print(f"{'='*70}\n")

    posts = await live_crawler.fetch_thread(args.url, max_pages=args.pages)

    print(f"\n{'='*70}")
    print(f"EXTRACTED {len(posts)} TOTAL POSTS")
    print(f"{'='*70}\n")

    # Filter by date if specified
    if args.since:
        from dateparser import parse as parse_date
        cutoff_date = parse_date(args.since)
        if cutoff_date:
            # Make timezone-aware
            if cutoff_date.tzinfo is None:
                from datetime import timezone
                cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)

            posts = live_crawler.crawler.filter_posts_by_date(posts, after=cutoff_date)
            print(f"After date filter (since {args.since}): {len(posts)} posts\n")

    # Calculate relevance and filter
    relevant_posts = live_crawler.crawler.filter_posts_by_relevance(
        posts,
        min_score=args.min_score
    )

    print(f"{'='*70}")
    print(f"RELEVANCE FILTERING (min score: {args.min_score})")
    print(f"{'='*70}\n")
    print(f"Relevant posts: {len(relevant_posts)}/{len(posts)}")
    print(f"Filtered out: {len(posts) - len(relevant_posts)}\n")

    # Show top posts
    relevant_posts_sorted = sorted(relevant_posts, key=lambda p: p.relevance_score, reverse=True)

    print(f"{'='*70}")
    print(f"TOP RELEVANT POSTS")
    print(f"{'='*70}\n")

    for i, post in enumerate(relevant_posts_sorted[:10], 1):
        print(f"{i}. Post {post.post_number} by {post.author}")
        print(f"   Score: {post.relevance_score:.1f}/100")
        print(f"   Time: {post.timestamp}")
        print(f"   Length: {len(post.content)} chars")
        if post.attachments:
            print(f"   Attachments: {', '.join(a['name'] for a in post.attachments)}")
        print(f"   Content: {post.content[:100]}...")
        print(f"   URL: {post.url}")
        print()

    # Save to JSON
    output_data = {
        'crawl_date': datetime.now().isoformat(),
        'thread_url': args.url,
        'total_posts': len(posts),
        'relevant_posts': len(relevant_posts),
        'min_score': args.min_score,
        'posts': [p.to_dict() for p in relevant_posts_sorted]
    }

    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"{'='*70}")
    print(f"Results saved to: {args.output}")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    asyncio.run(main())
