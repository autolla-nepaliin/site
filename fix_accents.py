#!/usr/bin/env python3
"""Remove accented characters from filenames and update references."""
import os
import re
import unicodedata
from pathlib import Path

DIST_DIR = Path("dist")
CONTENT_DIR = Path("content")

def remove_accents(text):
    """Remove accented characters from text."""
    # Normalize to NFC first (compose characters)
    text = unicodedata.normalize('NFC', text)
    replacements = {
        'ä': 'a', 'Ä': 'A',
        'ö': 'o', 'Ö': 'O',
        'å': 'a', 'Å': 'A',
        'ü': 'u', 'Ü': 'U',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u',
        'ý': 'y', 'ÿ': 'y',
        'ñ': 'n', 'ç': 'c',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def main():
    uploads_dir = DIST_DIR / "assets" / "uploads"
    renames = {}  # old_url -> new_url

    # Find and rename files
    print("Finding files with accented characters...")
    for f in sorted(uploads_dir.iterdir()):
        if f.is_file():
            old_name = f.name
            # Normalize old_name for comparison (macOS uses NFD)
            old_name_normalized = unicodedata.normalize('NFC', old_name)
            new_name = remove_accents(old_name)
            if old_name_normalized != new_name:
                # Store both NFD and NFC versions of old URL for replacement
                old_url_nfd = f"/assets/uploads/{old_name}"
                old_url_nfc = f"/assets/uploads/{old_name_normalized}"
                new_url = f"/assets/uploads/{new_name}"
                renames[old_url_nfd] = new_url
                renames[old_url_nfc] = new_url

                new_path = f.parent / new_name
                print(f"  {old_name_normalized} -> {new_name}")
                f.rename(new_path)

    print(f"\nRenamed {len(renames)} files")

    if not renames:
        return

    # Update HTML files
    print("\nUpdating HTML files...")
    html_count = 0
    for html_file in DIST_DIR.rglob("*.html"):
        content = html_file.read_text(encoding='utf-8')
        new_content = content
        for old_url, new_url in renames.items():
            new_content = new_content.replace(old_url, new_url)
        if new_content != content:
            html_file.write_text(new_content, encoding='utf-8')
            html_count += 1
    print(f"  Updated {html_count} HTML files")

    # Update markdown files
    print("\nUpdating markdown files...")
    md_count = 0
    for md_file in CONTENT_DIR.rglob("*.md"):
        content = md_file.read_text(encoding='utf-8')
        new_content = content
        for old_url, new_url in renames.items():
            new_content = new_content.replace(old_url, new_url)
        if new_content != content:
            md_file.write_text(new_content, encoding='utf-8')
            md_count += 1
            print(f"  Updated: {md_file}")
    print(f"  Updated {md_count} markdown files")

    # Update index.json
    print("\nUpdating index.json...")
    index_file = CONTENT_DIR / "index.json"
    if index_file.exists():
        content = index_file.read_text(encoding='utf-8')
        new_content = content
        for old_url, new_url in renames.items():
            new_content = new_content.replace(old_url, new_url)
        if new_content != content:
            index_file.write_text(new_content, encoding='utf-8')
            print("  Updated index.json")

    print("\nDone!")

if __name__ == '__main__':
    main()
