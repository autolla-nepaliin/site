#!/usr/bin/env python3
"""Crawl autollanepaliin.fi and export all URLs to CSV for migration verification."""

import csv
import re
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser
from collections import deque
import ssl

BASE_URL = "https://autollanepaliin.fi"
OUTPUT_FILE = "site_urls.csv"

# Disable SSL verification for simplicity
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

class LinkExtractor(HTMLParser):
    """Extract links, images, scripts from HTML."""

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = []
        self.images = []
        self.scripts = []
        self.stylesheets = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'a':
            href = attrs_dict.get('href')
            if href:
                self.links.append(urljoin(self.base_url, href))

        elif tag == 'link':
            href = attrs_dict.get('href')
            rel = attrs_dict.get('rel', '')
            if href:
                if 'stylesheet' in rel:
                    self.stylesheets.append(urljoin(self.base_url, href))
                else:
                    self.links.append(urljoin(self.base_url, href))

        elif tag == 'img':
            src = attrs_dict.get('src') or attrs_dict.get('data-src')
            if src:
                self.images.append(urljoin(self.base_url, src))
            # Handle srcset
            srcset = attrs_dict.get('srcset', '')
            for part in srcset.split(','):
                src = part.strip().split()[0] if part.strip() else ''
                if src:
                    self.images.append(urljoin(self.base_url, src))

        elif tag == 'script':
            src = attrs_dict.get('src')
            if src:
                self.scripts.append(urljoin(self.base_url, src))

        elif tag == 'source':
            srcset = attrs_dict.get('srcset', '')
            for part in srcset.split(','):
                src = part.strip().split()[0] if part.strip() else ''
                if src:
                    self.images.append(urljoin(self.base_url, src))

        # Check style attribute for background images
        style = attrs_dict.get('style', '')
        if style:
            urls_in_style = re.findall(r'url\(["\']?([^"\'()]+)["\']?\)', style)
            for src in urls_in_style:
                self.images.append(urljoin(self.base_url, src))

def is_internal_url(url):
    """Check if URL belongs to autollanepaliin.fi."""
    parsed = urlparse(url)
    return parsed.netloc in ('', 'autollanepaliin.fi', 'www.autollanepaliin.fi')

def normalize_url(url):
    """Normalize URL for deduplication."""
    parsed = urlparse(url)
    path = parsed.path.rstrip('/') or '/'
    netloc = parsed.netloc.replace('www.', '')
    return f"{parsed.scheme}://{netloc}{path}"

def get_url_type(url):
    """Determine the type of resource."""
    path = urlparse(url).path.lower()
    if re.search(r'\.(jpg|jpeg|png|gif|webp|svg|ico)$', path):
        return 'image'
    elif re.search(r'\.(css)$', path):
        return 'css'
    elif re.search(r'\.(js)$', path):
        return 'js'
    elif re.search(r'\.(pdf|doc|docx|xls|xlsx)$', path):
        return 'document'
    elif re.search(r'\.(mp4|webm|mov|avi)$', path):
        return 'video'
    elif re.search(r'\.(mp3|wav|ogg)$', path):
        return 'audio'
    elif re.search(r'\.(woff|woff2|ttf|eot)$', path):
        return 'font'
    elif '/wp-content/uploads/' in path:
        return 'upload'
    elif '/wp-admin/' in path or '/wp-login' in path:
        return 'admin'
    else:
        return 'page'

def fetch_url(url):
    """Fetch URL and return (status_code, content)."""
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; MigrationCrawler/1.0)'})
        response = urlopen(req, timeout=10, context=ssl_context)
        return response.status, response.read().decode('utf-8', errors='ignore')
    except HTTPError as e:
        return e.code, None
    except URLError as e:
        return 'error', None
    except Exception as e:
        return 'error', None

def crawl_site():
    """Crawl the site and collect all URLs."""
    visited = set()
    to_visit = deque([BASE_URL])
    urls_found = []

    print(f"Starting crawl of {BASE_URL}")

    while to_visit:
        url = to_visit.popleft()
        normalized = normalize_url(url)

        if normalized in visited:
            continue
        visited.add(normalized)

        # Skip admin URLs
        if '/wp-admin/' in url or '/wp-login' in url:
            continue

        url_type = get_url_type(url)

        # Only fetch HTML pages for link extraction
        if url_type not in ('page',):
            urls_found.append({
                'url': url,
                'type': url_type,
                'status': 'not_checked',
                'found_on': ''
            })
            continue

        status, content = fetch_url(url)

        urls_found.append({
            'url': url,
            'type': url_type,
            'status': status,
            'found_on': ''
        })

        if status != 200 or not content:
            print(f"  [{status}] {url}")
            continue

        print(f"  [200] {url} ({len(visited)} visited, {len(to_visit)} queued)")

        # Parse HTML and extract links
        try:
            parser = LinkExtractor(url)
            parser.feed(content)

            # Add page links to crawl queue
            for link in parser.links:
                if is_internal_url(link) and normalize_url(link) not in visited:
                    to_visit.append(link)

            # Add images
            for img in parser.images:
                if is_internal_url(img) and normalize_url(img) not in visited:
                    urls_found.append({
                        'url': img,
                        'type': 'image',
                        'status': 'not_checked',
                        'found_on': url
                    })
                    visited.add(normalize_url(img))

            # Add scripts
            for script in parser.scripts:
                if is_internal_url(script) and normalize_url(script) not in visited:
                    urls_found.append({
                        'url': script,
                        'type': 'js',
                        'status': 'not_checked',
                        'found_on': url
                    })
                    visited.add(normalize_url(script))

            # Add stylesheets
            for css in parser.stylesheets:
                if is_internal_url(css) and normalize_url(css) not in visited:
                    urls_found.append({
                        'url': css,
                        'type': 'css',
                        'status': 'not_checked',
                        'found_on': url
                    })
                    visited.add(normalize_url(css))

        except Exception as e:
            print(f"  [PARSE ERROR] {url}: {e}")

    return urls_found

def save_to_csv(urls, filename):
    """Save URLs to CSV file."""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['url', 'type', 'status', 'found_on'])
        writer.writeheader()
        writer.writerows(urls)
    print(f"\nSaved {len(urls)} URLs to {filename}")

def main():
    urls = crawl_site()

    # Sort by type and URL
    urls.sort(key=lambda x: (x['type'], x['url']))

    save_to_csv(urls, OUTPUT_FILE)

    # Print summary
    types = {}
    for u in urls:
        types[u['type']] = types.get(u['type'], 0) + 1

    print("\nSummary:")
    for t, count in sorted(types.items()):
        print(f"  {t}: {count}")

if __name__ == '__main__':
    main()
