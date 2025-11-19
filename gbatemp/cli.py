#!/usr/bin/env python3
"""
GBAtemp Crawler CLI
Command-line interface for crawling GBAtemp forums.
"""

import asyncio
import argparse
import json
from datetime import datetime, timezone
from dateparser import parse as parse_date

from .crawler import GBATempSimpleCrawler


async def main():
    """CLI interface for the crawler."""
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


def run():
    """Entry point for the CLI."""
    asyncio.run(main())


if __name__ == '__main__':
    run()
