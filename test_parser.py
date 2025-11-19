#!/usr/bin/env python3
"""Test the GBAtemp parser with real HTML samples."""

from gbatemp_crawler import GBATempCrawler
from datetime import datetime, timedelta

def main():
    # Read the test HTML
    with open('test_samples.html', 'r') as f:
        html = f.read()

    crawler = GBATempCrawler()

    print("=" * 70)
    print("GBATEMP POST PARSER TEST")
    print("=" * 70)

    # Parse posts
    posts = crawler.extract_posts_from_html(html)

    print(f"\n✓ Extracted {len(posts)} posts\n")

    # Analyze each post
    for i, post in enumerate(posts, 1):
        relevance = post.calculate_relevance()

        print(f"\n{'=' * 70}")
        print(f"POST #{i}: {post.post_number}")
        print(f"{'=' * 70}")
        print(f"Author:       {post.author}")
        print(f"Timestamp:    {post.timestamp}")
        print(f"Post ID:      {post.post_id}")
        print(f"URL:          {post.url}")
        print(f"\nContent ({len(post.content)} chars):")
        print("-" * 70)
        print(post.content[:300])
        if len(post.content) > 300:
            print(f"... ({len(post.content) - 300} more characters)")
        print("-" * 70)

        if post.attachments:
            print(f"\nAttachments ({len(post.attachments)}):")
            for att in post.attachments:
                print(f"  - {att['name']} ({att['size']})")

        if post.reactions:
            print(f"\nReactions: {post.reactions}")

        print(f"\n{'🎯 RELEVANCE SCORE: ' + str(relevance)}/100")

        if relevance >= 50:
            verdict = "✅ HIGHLY RELEVANT"
        elif relevance >= 20:
            verdict = "✓ RELEVANT"
        else:
            verdict = "✗ IRRELEVANT (FILTERED OUT)"

        print(f"{verdict}")

    # Test date filtering
    print(f"\n\n{'=' * 70}")
    print("DATE FILTERING TEST")
    print(f"{'=' * 70}")

    # Filter posts from last hour
    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent = crawler.filter_posts_by_date(posts, after=one_hour_ago)
    print(f"Posts from last hour: {len(recent)}/{len(posts)}")

    # Filter posts from last 24 hours
    one_day_ago = datetime.now() - timedelta(days=1)
    last_24h = crawler.filter_posts_by_date(posts, after=one_day_ago)
    print(f"Posts from last 24 hours: {len(last_24h)}/{len(posts)}")

    # Test relevance filtering
    print(f"\n\n{'=' * 70}")
    print("RELEVANCE FILTERING TEST")
    print(f"{'=' * 70}")

    relevant = crawler.filter_posts_by_relevance(posts, min_score=20)
    print(f"Relevant posts (score >= 20): {len(relevant)}/{len(posts)}")

    highly_relevant = crawler.filter_posts_by_relevance(posts, min_score=50)
    print(f"Highly relevant posts (score >= 50): {len(highly_relevant)}/{len(posts)}")

    # Show which posts passed the filter
    print(f"\n✓ PASSED RELEVANCE FILTER (>= 20):")
    for post in relevant:
        print(f"  - Post {post.post_number} by {post.author} (score: {post.relevance_score:.1f})")

    print(f"\n✗ FILTERED OUT:")
    filtered_out = [p for p in posts if p not in relevant]
    for post in filtered_out:
        print(f"  - Post {post.post_number} by {post.author} (score: {post.relevance_score:.1f})")

    print(f"\n{'=' * 70}")
    print("TEST COMPLETE")
    print(f"{'=' * 70}\n")


if __name__ == '__main__':
    main()
