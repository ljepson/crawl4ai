#!/usr/bin/env python3
"""
GBAtemp Forum Crawler - Simple CLI wrapper

Usage:
    python crawl_gbatemp.py --url "https://gbatemp.net/threads/..." --pages 5
    python crawl_gbatemp.py --url "..." --since "2 hours ago" --pages 10
"""

from gbatemp.cli import run

if __name__ == '__main__':
    run()
