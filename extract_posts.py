#!/usr/bin/env python3
"""Extract WordPress posts from SQL dump and convert to markdown."""

import re
import json
import html
from pathlib import Path
from datetime import datetime

# Read the SQL file
sql_file = Path("autollanepaliin-fi-20260125-181910-35wxexj3jdch/database.sql")
content = sql_file.read_text(encoding='utf-8', errors='replace')

# Find all INSERT statements for posts table
# Pattern: INSERT INTO `SERVMASK_PREFIX_posts` VALUES (id,author,date,date_gmt,content,title,...);
posts_pattern = re.compile(
    r"INSERT INTO `SERVMASK_PREFIX_posts` VALUES \((.+?)\);",
    re.DOTALL
)

def parse_sql_value(s):
    """Parse a single SQL value (handles quoted strings, numbers, NULL)."""
    s = s.strip()
    if s == 'NULL':
        return None
    if s.startswith("'"):
        # Remove quotes and unescape
        s = s[1:-1] if s.endswith("'") else s[1:]
        s = s.replace("\\'", "'").replace("\\\\", "\\").replace("\\n", "\n").replace("\\r", "\r")
        return s
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s

def split_sql_values(row):
    """Split SQL INSERT values, respecting quoted strings."""
    values = []
    current = []
    in_string = False
    escape_next = False

    for char in row:
        if escape_next:
            current.append(char)
            escape_next = False
            continue

        if char == '\\' and in_string:
            current.append(char)
            escape_next = True
            continue

        if char == "'" and not escape_next:
            current.append(char)
            in_string = not in_string
            continue

        if char == ',' and not in_string:
            values.append(''.join(current))
            current = []
            continue

        current.append(char)

    if current:
        values.append(''.join(current))

    return values

# Extract posts
posts = []
for match in posts_pattern.finditer(content):
    row = match.group(1)
    values = split_sql_values(row)

    if len(values) >= 23:
        post = {
            'id': parse_sql_value(values[0]),
            'author': parse_sql_value(values[1]),
            'date': parse_sql_value(values[2]),
            'date_gmt': parse_sql_value(values[3]),
            'content': parse_sql_value(values[4]),
            'title': parse_sql_value(values[5]),
            'excerpt': parse_sql_value(values[6]),
            'status': parse_sql_value(values[7]),
            'comment_status': parse_sql_value(values[8]),
            'ping_status': parse_sql_value(values[9]),
            'password': parse_sql_value(values[10]),
            'slug': parse_sql_value(values[11]),
            'to_ping': parse_sql_value(values[12]),
            'pinged': parse_sql_value(values[13]),
            'modified': parse_sql_value(values[14]),
            'modified_gmt': parse_sql_value(values[15]),
            'content_filtered': parse_sql_value(values[16]),
            'parent': parse_sql_value(values[17]),
            'guid': parse_sql_value(values[18]),
            'menu_order': parse_sql_value(values[19]),
            'type': parse_sql_value(values[20]),
            'mime_type': parse_sql_value(values[21]),
            'comment_count': parse_sql_value(values[22]),
        }
        posts.append(post)

# Filter published posts and pages
published_posts = [p for p in posts if p['status'] == 'publish' and p['type'] == 'post']
published_pages = [p for p in posts if p['status'] == 'publish' and p['type'] == 'page']

print(f"Total posts in DB: {len(posts)}")
print(f"Published posts: {len(published_posts)}")
print(f"Published pages: {len(published_pages)}")

# Show post types
types = {}
for p in posts:
    t = p['type']
    types[t] = types.get(t, 0) + 1
print(f"\nPost types: {types}")

# Show some sample posts
print("\n=== Sample Published Posts ===")
for p in sorted(published_posts, key=lambda x: x['date'] or '', reverse=True)[:10]:
    print(f"- [{p['date']}] {p['title']} ({p['slug']})")

print("\n=== Published Pages ===")
for p in published_pages:
    print(f"- {p['title']} ({p['slug']})")

# Extract postmeta for featured images
postmeta_pattern = re.compile(
    r"INSERT INTO `SERVMASK_PREFIX_postmeta` VALUES \((\d+),(\d+),'_thumbnail_id','(\d+)'\);",
)

thumbnail_map = {}  # post_id -> attachment_id
for match in postmeta_pattern.finditer(content):
    post_id = int(match.group(2))
    attachment_id = int(match.group(3))
    thumbnail_map[post_id] = attachment_id

# Build attachment_id -> URL map from posts (attachments are post_type='attachment')
attachment_map = {}
for p in posts:
    if p['type'] == 'attachment' and p['guid']:
        attachment_map[p['id']] = p['guid']

# Add featured_image to posts
for p in published_posts:
    if p['id'] in thumbnail_map:
        att_id = thumbnail_map[p['id']]
        if att_id in attachment_map:
            p['featured_image'] = attachment_map[att_id]

print(f"Posts with featured images: {sum(1 for p in published_posts if p.get('featured_image'))}")

# Save to JSON for further processing
with open('posts.json', 'w', encoding='utf-8') as f:
    json.dump({'posts': published_posts, 'pages': published_pages}, f, ensure_ascii=False, indent=2)

print(f"\nSaved to posts.json")
