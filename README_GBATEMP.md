# GBAtemp Forum Crawler

Crawls GBAtemp Switch forums to find relevant technical posts while filtering out noise.

## 🎯 What It Does

1. **Crawls** GBAtemp forum threads to extract posts
2. **Filters by date** - Only show posts after a specified time
3. **Scores relevance** (0-100) based on:
   - Content length
   - Presence of code/hex values (+25 pts)
   - Attachments (+20 pts)
   - Version numbers (+15 pts)
   - Technical keywords (+10 pts)
   - Penalties for short questions (-30 pts)
4. **Filters out noise** - Removes "thanks", short questions, generic replies
5. **Outputs JSON** - Structured data for further processing

## 📋 Requirements

```bash
pip install beautifulsoup4 lxml dateparser httpx
```

## 🚀 Quick Start

### Basic Usage

```bash
python crawl_gbatemp.py \
  --url "https://gbatemp.net/threads/sys-patch.633517/" \
  --pages 5 \
  --min-score 20 \
  --output results.json
```

### Filter by Date (with Smart Reverse Crawling)

When you use `--since`, the crawler **automatically crawls backwards** from the newest posts, stopping early when it hits older content. This is **much faster** than crawling from page 1.

```bash
# Posts from last 2 hours (crawls last 5 pages backwards)
python crawl_gbatemp.py \
  --url "https://gbatemp.net/threads/sys-patch.633517/" \
  --since "2 hours ago" \
  --pages 5 \
  --min-score 30

# Posts since specific date (crawls last 10 pages)
python crawl_gbatemp.py \
  --url "https://gbatemp.net/threads/sys-patch.633517/" \
  --since "2025-11-15" \
  --pages 10 \
  --min-score 20

# Posts from last week (increase --pages if thread is very active)
python crawl_gbatemp.py \
  --url "https://gbatemp.net/threads/atmosphere.496832/" \
  --since "1 week ago" \
  --pages 20 \
  --min-score 25
```

**How it works:**
1. Detects the last page number (e.g., page 527)
2. Starts from page 527, works backwards to 518 (if --pages 10)
3. Stops early if oldest post on a page is older than `--since`
4. Saves bandwidth and time by not crawling ancient posts

### Show All Posts (Including Filtered)

```bash
python crawl_gbatemp.py \
  --url "https://gbatemp.net/threads/sys-patch.633517/" \
  --show-all
```

## 📊 Example Output

```
======================================================================
TOP RELEVANT POSTS
======================================================================

1. #1,000 by bth
   🎯 Score: 90.0/100
   📅 Time: 2025-11-19 17:07:04 UTC
   📝 Length: 796 chars
   📎 Attachments: atmosphere.zip
   💬 Preview: your question fails to understand why there should be a patch. the same reason the nim patch...
   🔗 URL: https://gbatemp.net/posts/10769525/

2. #1,002 by TechNinja
   🎯 Score: 75.5/100
   📅 Time: 2025-11-19 18:30:21 UTC
   📝 Length: 453 chars
   💬 Preview: Updated sigpatches for firmware 19.0.0. Tested and working. Download link: ...
   🔗 URL: https://gbatemp.net/posts/10769600/
```

## 🎓 How Relevance Scoring Works

### ✅ RELEVANT (High Score)

**Example: Score 90/100**
- Long technical explanation (796 chars)
- Contains hex code: `0x84F44, a9 c3 5f 38`
- Has attachment: `atmosphere.zip`
- Uses technical terms: patch, nim, sys-patch
- Got reactions from community

### ✗ IRRELEVANT (Low Score)

**Example: Score 12/100**
- Short question (106 chars)
- No code, no attachments
- Just asking for clarification
- Ends with "?"

## 📁 Package Structure

```
gbatemp/
  __init__.py       - Package exports
  parser.py         - GBATempPost class and relevance scoring
  crawler.py        - HTML extraction and HTTP crawling
  cli.py            - Command-line interface
  playwright.py     - Browser-based crawler (optional)

crawl_gbatemp.py    - Simple CLI wrapper (main entry point)
test_example_html.py - Test suite with sample HTML
```

## 🔧 Programmatic Usage

```python
import asyncio
from gbatemp import GBATempSimpleCrawler

async def main():
    crawler = GBATempSimpleCrawler()

    # Fetch posts
    posts = await crawler.fetch_thread(
        "https://gbatemp.net/threads/sys-patch.633517/",
        max_pages=3
    )

    # Filter by relevance
    relevant = crawler.crawler.filter_posts_by_relevance(
        posts,
        min_score=30
    )

    # Sort by score
    top_posts = sorted(relevant, key=lambda p: p.relevance_score, reverse=True)

    for post in top_posts[:10]:
        print(f"{post.author}: {post.relevance_score:.1f}/100")
        print(f"  {post.content[:100]}...")

asyncio.run(main())
```

## 🛡️ Dealing with Bot Detection

If you get **HTTP 403** errors, GBAtemp is blocking automated access:

### Option 1: Run Locally
Run from your personal machine (not a cloud server/container)

### Option 2: Use Browser Extension
1. Install "Save Page WE" or similar
2. Save thread pages as HTML
3. Parse locally:

```python
from gbatemp import GBATempCrawler

crawler = GBATempCrawler()

with open('thread_page.html', 'r') as f:
    html = f.read()

posts = crawler.extract_posts_from_html(html)
relevant = crawler.filter_posts_by_relevance(posts, min_score=20)

for post in relevant:
    print(f"{post.author}: {post.relevance_score}/100")
```

### Option 3: Add Delays
Modify `gbatemp/crawler.py` to add longer delays:

```python
await asyncio.sleep(5)  # Wait 5 seconds between requests
```

## 📈 Adjusting Relevance Thresholds

Edit `gbatemp/parser.py` → `GBATempPost.calculate_relevance()`:

```python
# Make scoring stricter
if content_len > 500:
    score += 30  # Increase from 20

# Add new detection patterns
if 'firmware' in self.content.lower():
    score += 10

# Harsher penalties
if content_len < 50:
    score -= 50  # Very short posts get crushed
```

## 🎯 Use Cases

### 1. Find Latest Updates
```bash
python crawl_gbatemp.py \
  --url "https://gbatemp.net/forums/nintendo-switch.283/" \
  --since "1 hour ago" \
  --min-score 50
```

### 2. Extract Technical Posts Only
```bash
python crawl_gbatemp.py \
  --url "https://gbatemp.net/threads/atmosphere.634821/" \
  --min-score 60  # Very strict
```

### 3. Monitor Multiple Threads
```bash
#!/bin/bash
for thread in thread1 thread2 thread3; do
  python crawl_gbatemp.py \
    --url "https://gbatemp.net/threads/$thread/" \
    --since "30 minutes ago" \
    --output "${thread}_results.json"
done
```

## 🐛 Troubleshooting

### No Posts Extracted
- Check URL is correct
- Try without `/page-X` suffix first
- Save HTML manually and test parser with `test_parser.py`

### All Posts Filtered Out
- Lower `--min-score` threshold (try 10)
- Use `--show-all` to see what was filtered
- Check if date filter is too restrictive

### HTTP 403 Errors
- GBAtemp is blocking you
- See "Dealing with Bot Detection" section above

## 📝 License

Open source - use however you want.

## 🙏 Credits

Built with:
- BeautifulSoup4 for HTML parsing
- dateparser for flexible date parsing
- httpx for async HTTP requests
