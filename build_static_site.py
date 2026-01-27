#!/usr/bin/env python3
"""Build static site from WordPress backup with markdown content."""

import json
import re
import os
import shutil
from pathlib import Path
from datetime import datetime
import html
import urllib.parse

# Configuration
SITE_URL = "https://autollanepaliin.fi"
OUTPUT_DIR = Path("dist")
CONTENT_DIR = Path("content")
POSTS_DIR = CONTENT_DIR / "posts"
PAGES_DIR = CONTENT_DIR / "pages"
ASSETS_DIR = OUTPUT_DIR / "assets"
UPLOADS_SRC = Path("autollanepaliin-fi-20260125-181910-35wxexj3jdch/uploads")

def html_to_markdown(content):
    """Convert WordPress HTML content to Markdown."""
    if not content:
        return ""

    # Decode HTML entities
    text = html.unescape(content)

    # Handle WordPress shortcodes - caption
    def convert_caption(match):
        inner = match.group(1)
        # Unescape quotes first
        inner_unesc = inner.replace('\\"', '"').replace("\\'", "'")
        # Extract image and caption text
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*/?>', inner_unesc, re.IGNORECASE)
        caption_text = re.sub(r'<[^>]+>', '', inner_unesc).strip()
        if img_match:
            img_url = img_match.group(1)
            # Convert to relative URL
            img_url = convert_url(img_url)
            return f'\n![{caption_text}]({img_url})\n*{caption_text}*\n'
        return caption_text

    text = re.sub(r'\[caption[^\]]*\](.*?)\[/caption\]', convert_caption, text, flags=re.DOTALL | re.IGNORECASE)

    # Handle WordPress column shortcodes - use marker that survives HTML stripping
    # These will be converted to grid layout in generate_html.py
    text = re.sub(r'\[column[^\]]*\]', '\n:::card\n', text, flags=re.IGNORECASE)
    text = re.sub(r'\[/column\]', '\n:::endcard\n', text, flags=re.IGNORECASE)

    # Convert images
    def convert_img(match):
        full = match.group(0).replace('\\"', '"').replace("\\'", "'")
        src_match = re.search(r'src=["\']([^"\']+)["\']', full)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', full)
        title_match = re.search(r'title=["\']([^"\']*)["\']', full)

        if src_match:
            src = convert_url(src_match.group(1))
            alt = alt_match.group(1) if alt_match else ""
            title = title_match.group(1) if title_match else alt
            return f'![{alt or title}]({src})'
        return ''

    text = re.sub(r'<img[^>]+/?>', convert_img, text, flags=re.IGNORECASE)

    # Convert links
    def convert_link(match):
        full = match.group(0)
        href_match = re.search(r'href=["\']([^"\']+)["\']', full)
        content = match.group(1)
        # Remove nested tags from link text
        link_text = re.sub(r'<[^>]+>', '', content).strip()

        if href_match:
            href = convert_url(href_match.group(1))
            return f'[{link_text}]({href})'
        return link_text

    text = re.sub(r'<a[^>]*>(.*?)</a>', convert_link, text, flags=re.DOTALL | re.IGNORECASE)

    # Convert headings
    for i in range(6, 0, -1):
        text = re.sub(rf'<h{i}[^>]*>(.*?)</h{i}>', r'\n' + '#' * i + r' \1\n', text, flags=re.IGNORECASE | re.DOTALL)

    # Convert bold/strong
    text = re.sub(r'<(?:strong|b)>(.*?)</(?:strong|b)>', r'**\1**', text, flags=re.IGNORECASE | re.DOTALL)

    # Convert italic/em
    text = re.sub(r'<(?:em|i)>(.*?)</(?:em|i)>', r'*\1*', text, flags=re.IGNORECASE | re.DOTALL)

    # Convert lists
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'</?(?:ul|ol)[^>]*>', '\n', text, flags=re.IGNORECASE)

    # Convert paragraphs
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', text, flags=re.IGNORECASE | re.DOTALL)

    # Convert blockquotes
    text = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', lambda m: '\n> ' + m.group(1).replace('\n', '\n> ') + '\n', text, flags=re.IGNORECASE | re.DOTALL)

    # Convert line breaks
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)

    # Convert horizontal rules
    text = re.sub(r'<hr\s*/?>', '\n---\n', text, flags=re.IGNORECASE)

    # Remove remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()

    # Clean up card content - remove list markers that don't make sense
    def clean_card_content(match):
        card_content = match.group(1)
        # Remove leading '- ' from lines inside cards (came from <li> conversion)
        card_content = re.sub(r'^\s*- ', '', card_content, flags=re.MULTILINE)
        # Clean up 'email' and 'www' labels
        card_content = re.sub(r'^email\s+', 'Email: ', card_content, flags=re.MULTILINE)
        card_content = re.sub(r'^www\s+', 'Web: ', card_content, flags=re.MULTILINE)
        return f':::card\n{card_content}\n:::endcard'

    text = re.sub(r':::card\n(.*?)\n:::endcard', clean_card_content, text, flags=re.DOTALL)

    return text

def convert_url(url):
    """Convert WordPress URLs to static site URLs."""
    if not url:
        return url

    # Convert WordPress upload URLs to local
    patterns = [
        (r'https?://autollanepaliin\.fi/wordpress/wp-content/uploads/(.+)', r'/assets/uploads/\1'),
        (r'https?://autollanepaliin\.fi/wp-content/uploads/(.+)', r'/assets/uploads/\1'),
        (r'/wordpress/wp-content/uploads/(.+)', r'/assets/uploads/\1'),
        (r'/wp-content/uploads/(.+)', r'/assets/uploads/\1'),
    ]

    for pattern, replacement in patterns:
        url = re.sub(pattern, replacement, url)

    # Convert internal post/page links
    url = re.sub(r'https?://autollanepaliin\.fi/wordpress/(.+)', r'/\1', url)
    url = re.sub(r'https?://autollanepaliin\.fi/(.+)', r'/\1', url)

    return url

def slugify(text):
    """Create a URL-safe slug from text."""
    text = text.lower()
    text = re.sub(r'[äå]', 'a', text)
    text = re.sub(r'ö', 'o', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = text.strip('-')
    return text

def extract_first_image(content):
    """Extract first image URL from HTML content."""
    if not content:
        return None
    # Unescape quotes for matching
    unescaped = content.replace('\\"', '"').replace("\\'", "'")
    # Look for img tags in HTML content
    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', unescaped, re.IGNORECASE)
    if img_match:
        return convert_url(img_match.group(1))
    return None

def create_frontmatter(post, post_type='post', content_image=None):
    """Create YAML frontmatter for markdown file."""
    date = post['date'] or ''
    if date:
        try:
            dt = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            date = dt.strftime('%Y-%m-%d')
        except:
            pass

    lines = [
        '---',
        f'title: "{(post["title"] or "").replace("\"", "\\\"")}"',
        f'slug: "{post["slug"] or ""}"',
        f'date: "{date}"',
        f'type: "{post_type}"',
    ]

    if post.get('excerpt'):
        excerpt = post['excerpt'].replace('"', '\\"').replace('\n', ' ')[:200]
        lines.append(f'excerpt: "{excerpt}"')

    # Use featured_image if available, otherwise use first image from content
    featured = post.get('featured_image')
    if featured:
        featured = convert_url(featured)
    elif content_image:
        featured = content_image

    if featured:
        lines.append(f'featured_image: "{featured}"')

    lines.append('---')
    return '\n'.join(lines)

def main():
    # Load posts data
    with open('posts.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    posts = data['posts']
    pages = data['pages']

    # Create directories
    for d in [OUTPUT_DIR, CONTENT_DIR, POSTS_DIR, PAGES_DIR, ASSETS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # Copy uploads
    uploads_dest = ASSETS_DIR / 'uploads'
    if UPLOADS_SRC.exists() and not uploads_dest.exists():
        print(f"Copying uploads to {uploads_dest}...")
        shutil.copytree(UPLOADS_SRC, uploads_dest)

    # Sort posts by date
    posts = sorted(posts, key=lambda x: x['date'] or '', reverse=True)

    # Convert posts to markdown
    print(f"\nConverting {len(posts)} posts to markdown...")
    for post in posts:
        slug = post['slug'] or slugify(post['title'] or str(post['id']))
        date = post['date'] or ''
        date_prefix = ''
        if date:
            try:
                dt = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                date_prefix = dt.strftime('%Y-%m-%d-')
            except:
                pass

        filename = f"{date_prefix}{slug}.md"
        filepath = POSTS_DIR / filename

        # Extract first image from content if no featured image
        content_image = None
        if not post.get('featured_image'):
            content_image = extract_first_image(post['content'])

        frontmatter = create_frontmatter(post, 'post', content_image)
        content = html_to_markdown(post['content'])

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter)
            f.write('\n\n')
            f.write(content)

        print(f"  Created: {filename}")

    # Convert pages to markdown
    print(f"\nConverting {len(pages)} pages to markdown...")
    for page in pages:
        slug = page['slug'] or slugify(page['title'] or str(page['id']))
        filename = f"{slug}.md"
        filepath = PAGES_DIR / filename

        frontmatter = create_frontmatter(page, 'page')
        content = html_to_markdown(page['content'])

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(frontmatter)
            f.write('\n\n')
            f.write(content)

        print(f"  Created: {filename}")

    # Create index of all content
    def get_post_image(p):
        """Get featured image or first content image."""
        if p.get('featured_image'):
            return convert_url(p['featured_image'])
        return extract_first_image(p.get('content'))

    index = {
        'posts': [
            {
                'slug': p['slug'],
                'title': p['title'],
                'date': p['date'],
                'excerpt': (html_to_markdown(p['excerpt']) or html_to_markdown(p['content'] or '')[:200]),
                'featured_image': get_post_image(p)
            }
            for p in posts
        ],
        'pages': [
            {
                'slug': p['slug'],
                'title': p['title']
            }
            for p in pages
        ]
    }

    with open(CONTENT_DIR / 'index.json', 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Created content index at {CONTENT_DIR / 'index.json'}")
    print(f"✓ Posts: {len(posts)} files in {POSTS_DIR}")
    print(f"✓ Pages: {len(pages)} files in {PAGES_DIR}")
    print(f"✓ Assets: {uploads_dest}")

if __name__ == '__main__':
    main()
