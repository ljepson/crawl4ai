#!/usr/bin/env python3
"""Test parser on the example HTML file provided by user."""

from gbatemp_crawler import GBATempCrawler

def main():
    # Read the example HTML
    with open('example_post_gbatemp.html', 'r') as f:
        html = f.read()

    crawler = GBATempCrawler()

    print("=" * 70)
    print("PARSING EXAMPLE HTML FROM USER")
    print("=" * 70)

    # Parse posts
    posts = crawler.extract_posts_from_html(html)

    print(f"\n✓ Extracted {len(posts)} posts\n")

    # Calculate relevance for all
    for post in posts:
        post.calculate_relevance()

    # Sort by relevance
    posts_sorted = sorted(posts, key=lambda p: p.relevance_score, reverse=True)

    print("=" * 70)
    print("ALL POSTS (sorted by relevance)")
    print("=" * 70)

    for i, post in enumerate(posts_sorted, 1):
        print(f"\n{i}. Post {post.post_number} by {post.author}")
        print(f"   🎯 Score: {post.relevance_score:.1f}/100")
        print(f"   📅 Time: {post.timestamp}")
        print(f"   📝 Length: {len(post.content)} chars")
        if post.attachments:
            print(f"   📎 Attachments: {', '.join(a['name'] for a in post.attachments)}")
        if post.reactions:
            print(f"   👍 Reactions: {post.reactions}")
        print(f"   💬 Content: {post.content[:150]}...")

    # Filter by relevance >= 20
    relevant = crawler.filter_posts_by_relevance(posts, min_score=20)

    print(f"\n{'=' * 70}")
    print(f"SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total posts: {len(posts)}")
    print(f"Relevant (score >= 20): {len(relevant)}")
    print(f"Filtered out: {len(posts) - len(relevant)}")

    if relevant:
        avg_score = sum(p.relevance_score for p in relevant) / len(relevant)
        print(f"Average relevance score: {avg_score:.1f}/100")

        posts_with_code = sum(1 for p in relevant if '0x' in p.content or '```' in p.content)
        print(f"Posts with code: {posts_with_code}")

        posts_with_attachments = sum(1 for p in relevant if p.attachments)
        print(f"Posts with attachments: {posts_with_attachments}")

    print()


if __name__ == '__main__':
    main()
