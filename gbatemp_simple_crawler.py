#!/usr/bin/env python3
"""
Simple GBAtemp Crawler - Uses HTTP requests without browser automation.
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import List
from gbatemp_crawler import GBATempCrawler, GBATempPost


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
        from bs4 import BeautifulSoup
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
                # Fetch first page to get total page count
                print(f"Detecting last page number...")
                response = await client.get(thread_url)
                if response.status_code != 200:
                    print(f"  → Error: HTTP {response.status_code}")
                    return []

                last_page = self.get_last_page_number(response.text)
                print(f"  → Found {last_page} pages")

                # Crawl backwards from last page
                start_page = last_page
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


async def main():
    """CLI interface for the crawler."""
    import argparse

    parser = argparse.ArgumentParser(
        description='GBAtemp Forum Crawler (HTTP-based, no browser needed)'
    )
    parser.add_argument(
        '--url',
        type=str,
        required=True,
        help='Thread URL to crawl (e.g., https://gbatemp.net/threads/sys-patch.633517/)'
    )
    parser.add_argument(
        '--pages',
        type=int,
        default=1,
        help='Maximum pages to crawl (default: 1). Increase when using --since (e.g., --pages 10)'
    )
    parser.add_argument(
        '--min-score',
        type=float,
        default=20.0,
        help='Minimum relevance score 0-100 (default: 20)'
    )
    parser.add_argument(
        '--since',
        type=str,
        default=None,
        help='Filter posts after this date (e.g., "2025-11-19", "2 hours ago", "yesterday")'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='gbatemp_results.json',
        help='Output JSON file (default: gbatemp_results.json)'
    )
    parser.add_argument(
        '--show-all',
        action='store_true',
        help='Show all posts including filtered ones'
    )

    args = parser.parse_args()

    # Create crawler
    crawler = GBATempSimpleCrawler()

    print(f"\n{'='*70}")
    print("GBATEMP FORUM CRAWLER")
    print(f"{'='*70}\n")

    # Parse cutoff date if --since is provided
    cutoff_date = None
    reverse_crawl = False
    if args.since:
        from dateparser import parse as parse_date
        from datetime import timezone

        cutoff_date = parse_date(args.since)
        if cutoff_date:
            # Make timezone-aware
            if cutoff_date.tzinfo is None:
                cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)
            reverse_crawl = True
            print(f"🕒 Date filter active: showing posts since {args.since}")
            print(f"   Parsed as: {cutoff_date}")
            print(f"   Crawling backwards from newest posts...\n")

    # Fetch posts
    print(f"Target: {args.url}")
    print(f"Pages to crawl: {args.pages}")
    print(f"Min relevance score: {args.min_score}\n")

    posts = await crawler.fetch_thread(
        args.url,
        max_pages=args.pages,
        cutoff_date=cutoff_date,
        reverse=reverse_crawl
    )

    print(f"\n{'='*70}")
    print(f"EXTRACTED {len(posts)} TOTAL POSTS")
    print(f"{'='*70}\n")

    if not posts:
        print("No posts extracted. Possible reasons:")
        print("  - URL is incorrect")
        print("  - Thread doesn't exist")
        print("  - GBAtemp structure has changed")
        print("  - Network connectivity issues")
        if args.since:
            print(f"  - No posts found since {args.since} (try increasing --pages or different timeframe)")
        return

    # Filter by date if not already done during crawl
    filtered_by_date = posts
    if cutoff_date and not reverse_crawl:
        # Manual filtering (fallback if not reverse crawling)
        filtered_by_date = crawler.crawler.filter_posts_by_date(posts, after=cutoff_date)
        print(f"Date filter (since {args.since}):")
        print(f"  → Kept: {len(filtered_by_date)} posts")
        print(f"  → Filtered out: {len(posts) - len(filtered_by_date)} posts\n")

    # Calculate relevance and filter
    relevant_posts = crawler.crawler.filter_posts_by_relevance(
        filtered_by_date,
        min_score=args.min_score
    )

    print(f"{'='*70}")
    print(f"RELEVANCE FILTERING (min score: {args.min_score})")
    print(f"{'='*70}\n")
    print(f"Relevant posts: {len(relevant_posts)}")
    print(f"Filtered out: {len(filtered_by_date) - len(relevant_posts)}\n")

    # Sort by relevance score
    relevant_posts_sorted = sorted(relevant_posts, key=lambda p: p.relevance_score, reverse=True)

    # Show results
    print(f"{'='*70}")
    print(f"TOP RELEVANT POSTS")
    print(f"{'='*70}\n")

    for i, post in enumerate(relevant_posts_sorted[:20], 1):
        print(f"{i}. #{post.post_number} by {post.author}")
        print(f"   🎯 Score: {post.relevance_score:.1f}/100")
        print(f"   📅 Time: {post.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"   📝 Length: {len(post.content)} chars")
        if post.attachments:
            att_names = ', '.join(a['name'] for a in post.attachments)
            print(f"   📎 Attachments: {att_names}")
        print(f"   💬 Preview: {post.content[:100]}...")
        print(f"   🔗 URL: {post.url}")
        print()

    # Show filtered posts if requested
    if args.show_all:
        filtered_out = [p for p in filtered_by_date if p not in relevant_posts]
        if filtered_out:
            print(f"\n{'='*70}")
            print(f"FILTERED OUT POSTS ({len(filtered_out)})")
            print(f"{'='*70}\n")

            for i, post in enumerate(filtered_out[:10], 1):
                print(f"{i}. #{post.post_number} by {post.author} (score: {post.relevance_score:.1f})")
                print(f"   {post.content[:80]}...")
                print()

    # Save to JSON
    output_data = {
        'crawl_date': datetime.now().isoformat(),
        'thread_url': args.url,
        'pages_crawled': args.pages,
        'total_posts_extracted': len(posts),
        'posts_after_date_filter': len(filtered_by_date),
        'relevant_posts': len(relevant_posts),
        'min_score_threshold': args.min_score,
        'date_filter': args.since,
        'posts': [p.to_dict() for p in relevant_posts_sorted]
    }

    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"{'='*70}")
    print(f"✅ Results saved to: {args.output}")
    print(f"{'='*70}\n")

    # Summary statistics
    if relevant_posts:
        avg_score = sum(p.relevance_score for p in relevant_posts) / len(relevant_posts)
        posts_with_code = sum(1 for p in relevant_posts if any(pattern in p.content for pattern in ['0x', '```', 'void ', 'mov ']))
        posts_with_attachments = sum(1 for p in relevant_posts if p.attachments)

        print("📊 STATISTICS:")
        print(f"   Average relevance score: {avg_score:.1f}/100")
        print(f"   Posts with code: {posts_with_code}")
        print(f"   Posts with attachments: {posts_with_attachments}")
        print(f"   Most active author: {max(set(p.author for p in relevant_posts), key=lambda a: sum(1 for p in relevant_posts if p.author == a))}")
        print()


if __name__ == '__main__':
    asyncio.run(main())
