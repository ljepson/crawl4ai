#!/usr/bin/env python3
"""
Example: How to use the GBAtemp crawler in your own code.
"""

import asyncio
from datetime import datetime, timedelta
from gbatemp_simple_crawler import GBATempSimpleCrawler


async def example_basic():
    """Basic usage: Fetch and filter posts."""
    print("=" * 70)
    print("EXAMPLE 1: Basic Crawling")
    print("=" * 70 + "\n")

    crawler = GBATempSimpleCrawler()

    # Fetch posts from a thread
    posts = await crawler.fetch_thread(
        "https://gbatemp.net/threads/sys-patch-sysmod-that-patches-on-boot.633517/",
        max_pages=2
    )

    print(f"Fetched {len(posts)} posts\n")

    # Filter by relevance (min score 30)
    relevant = crawler.crawler.filter_posts_by_relevance(posts, min_score=30)

    print(f"Relevant posts (score >= 30): {len(relevant)}\n")

    # Show top 5
    top_posts = sorted(relevant, key=lambda p: p.relevance_score, reverse=True)[:5]

    for i, post in enumerate(top_posts, 1):
        print(f"{i}. {post.author} (score: {post.relevance_score:.1f})")
        print(f"   {post.content[:80]}...")
        print()


async def example_date_filtering():
    """Date filtering: Only show recent posts."""
    print("=" * 70)
    print("EXAMPLE 2: Date Filtering")
    print("=" * 70 + "\n")

    crawler = GBATempSimpleCrawler()

    posts = await crawler.fetch_thread(
        "https://gbatemp.net/threads/sys-patch-sysmod-that-patches-on-boot.633517/",
        max_pages=1
    )

    # Filter posts from last 24 hours
    cutoff = datetime.now().replace(tzinfo=datetime.now().astimezone().tzinfo) - timedelta(hours=24)

    recent_posts = crawler.crawler.filter_posts_by_date(posts, after=cutoff)

    print(f"Total posts: {len(posts)}")
    print(f"Posts from last 24h: {len(recent_posts)}\n")

    # Apply relevance filter
    relevant = crawler.crawler.filter_posts_by_relevance(recent_posts, min_score=20)

    print(f"Relevant recent posts: {len(relevant)}\n")


async def example_custom_filtering():
    """Custom filtering: Your own logic."""
    print("=" * 70)
    print("EXAMPLE 3: Custom Filtering")
    print("=" * 70 + "\n")

    crawler = GBATempSimpleCrawler()

    posts = await crawler.fetch_thread(
        "https://gbatemp.net/threads/sys-patch-sysmod-that-patches-on-boot.633517/",
        max_pages=1
    )

    # Calculate relevance for all posts
    for post in posts:
        post.calculate_relevance()

    # Custom filter: Posts with attachments AND high relevance
    posts_with_files = [
        p for p in posts
        if p.attachments and p.relevance_score >= 40
    ]

    print(f"Posts with attachments + score >= 40: {len(posts_with_files)}\n")

    for post in posts_with_files:
        print(f"- {post.author}: {post.relevance_score:.1f}/100")
        for att in post.attachments:
            print(f"  Attachment: {att['name']} ({att['size']})")
        print()


async def example_author_analysis():
    """Analyze posts by author."""
    print("=" * 70)
    print("EXAMPLE 4: Author Analysis")
    print("=" * 70 + "\n")

    crawler = GBATempSimpleCrawler()

    posts = await crawler.fetch_thread(
        "https://gbatemp.net/threads/sys-patch-sysmod-that-patches-on-boot.633517/",
        max_pages=3
    )

    # Calculate relevance
    for post in posts:
        post.calculate_relevance()

    # Group by author
    from collections import defaultdict
    author_stats = defaultdict(lambda: {'count': 0, 'total_score': 0, 'posts': []})

    for post in posts:
        author_stats[post.author]['count'] += 1
        author_stats[post.author]['total_score'] += post.relevance_score
        author_stats[post.author]['posts'].append(post)

    # Calculate averages
    for author, stats in author_stats.items():
        stats['avg_score'] = stats['total_score'] / stats['count']

    # Sort by average relevance
    top_authors = sorted(
        author_stats.items(),
        key=lambda x: x[1]['avg_score'],
        reverse=True
    )[:10]

    print("Top authors by average relevance:\n")

    for i, (author, stats) in enumerate(top_authors, 1):
        print(f"{i}. {author}")
        print(f"   Posts: {stats['count']}")
        print(f"   Avg Score: {stats['avg_score']:.1f}/100")
        print()


async def example_parse_local_html():
    """Parse HTML files saved locally."""
    print("=" * 70)
    print("EXAMPLE 5: Parse Local HTML Files")
    print("=" * 70 + "\n")

    from gbatemp_crawler import GBATempCrawler

    crawler = GBATempCrawler()

    # Read local HTML file (you saved this from your browser)
    try:
        with open('test_samples.html', 'r') as f:
            html = f.read()

        posts = crawler.extract_posts_from_html(html)
        print(f"Extracted {len(posts)} posts from local file\n")

        # Filter by relevance
        relevant = crawler.filter_posts_by_relevance(posts, min_score=20)

        print(f"Relevant posts: {len(relevant)}\n")

        for post in relevant:
            print(f"- {post.author} (score: {post.relevance_score:.1f})")
            print(f"  {post.content[:100]}...")
            print()

    except FileNotFoundError:
        print("test_samples.html not found - save a GBAtemp thread page as HTML first")


async def main():
    """Run all examples (will fail with HTTP 403 in cloud environments)."""

    # This example works offline with local HTML
    await example_parse_local_html()

    # These require network access and will fail if GBAtemp blocks you:
    # await example_basic()
    # await example_date_filtering()
    # await example_custom_filtering()
    # await example_author_analysis()


if __name__ == '__main__':
    asyncio.run(main())
