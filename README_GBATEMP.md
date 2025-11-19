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
python gbatemp_simple_crawler.py \
  --url "https://gbatemp.net/threads/sys-patch.633517/" \
  --pages 5 \
  --min-score 20 \
  --output results.json
```

### Filter by Date

```bash
# Posts from last 2 hours
python gbatemp_simple_crawler.py \
  --url "https://gbatemp.net/threads/sys-patch.633517/" \
  --since "2 hours ago" \
  --min-score 30

# Posts since specific date
python gbatemp_simple_crawler.py \
  --url "https://gbatemp.net/threads/sys-patch.633517/" \
  --since "2025-11-19" \
  --min-score 20
```

### Show All Posts (Including Filtered)

```bash
python gbatemp_simple_crawler.py \
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

## 📁 Files

- `gbatemp_crawler.py` - Core parser and relevance scoring
- `gbatemp_simple_crawler.py` - CLI tool (HTTP-based)
- `test_parser.py` - Test suite with sample HTML
- `test_samples.html` - Example posts for testing

## 🔧 Programmatic Usage

```python
import asyncio
from gbatemp_simple_crawler import GBATempSimpleCrawler

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
from gbatemp_crawler import GBATempCrawler

crawler = GBATempCrawler()

with open('thread_page.html', 'r') as f:
    html = f.read()

posts = crawler.extract_posts_from_html(html)
relevant = crawler.filter_posts_by_relevance(posts, min_score=20)

for post in relevant:
    print(f"{post.author}: {post.relevance_score}/100")
```

### Option 3: Add Delays
Modify `gbatemp_simple_crawler.py` to add longer delays:

```python
await asyncio.sleep(5)  # Wait 5 seconds between requests
```

## 📈 Adjusting Relevance Thresholds

Edit `gbatemp_crawler.py` → `GBATempPost.calculate_relevance()`:

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
python gbatemp_simple_crawler.py \
  --url "https://gbatemp.net/forums/nintendo-switch.283/" \
  --since "1 hour ago" \
  --min-score 50
```

### 2. Extract Technical Posts Only
```bash
python gbatemp_simple_crawler.py \
  --url "https://gbatemp.net/threads/atmosphere.634821/" \
  --min-score 60  # Very strict
```

### 3. Monitor Multiple Threads
```bash
#!/bin/bash
for thread in thread1 thread2 thread3; do
  python gbatemp_simple_crawler.py \
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
