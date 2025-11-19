"""
GBAtemp Forum Crawler Package

A specialized crawler for GBAtemp forums that:
- Crawls forum threads and extracts posts
- Filters by date and relevance
- Removes irrelevant content (short questions, generic responses)
- Returns only useful technical discussion

Usage:
    from gbatemp import GBATempSimpleCrawler, GBATempPost

    crawler = GBATempSimpleCrawler()
    posts = await crawler.fetch_thread("https://gbatemp.net/threads/...", max_pages=5)
"""

from .parser import GBATempPost
from .crawler import GBATempCrawler, GBATempSimpleCrawler
from .cli import main, run

# Optional: only import Playwright if available
try:
    from .playwright import GBATempLiveCrawler
    __all__ = [
        'GBATempPost',
        'GBATempCrawler',
        'GBATempSimpleCrawler',
        'GBATempLiveCrawler',
        'main',
        'run'
    ]
except ImportError:
    __all__ = [
        'GBATempPost',
        'GBATempCrawler',
        'GBATempSimpleCrawler',
        'main',
        'run'
    ]

__version__ = '1.0.0'
