#!/usr/bin/env python3
"""
GBAtemp Playwright Crawler
Browser-based crawling using Playwright (alternative to HTTP crawler).
"""

import asyncio
from typing import List
from playwright.async_api import async_playwright

from .crawler import GBATempCrawler
from .parser import GBATempPost


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
