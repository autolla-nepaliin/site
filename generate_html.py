#!/usr/bin/env python3
"""Generate static HTML site from markdown content."""

import json
import re
import os
from pathlib import Path
from datetime import datetime
import html

# Use mistune for markdown rendering if available, else simple fallback
try:
    import mistune
    md = mistune.create_markdown()
except ImportError:
    # Simple markdown converter fallback
    def md(text):
        """Simple markdown to HTML converter."""
        # Headers
        for i in range(6, 0, -1):
            text = re.sub(rf'^{"#" * i}\s+(.+)$', rf'<h{i}>\1</h{i}>', text, flags=re.MULTILINE)

        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

        # Italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

        # Images with alt text fallback from filename
        def img_with_alt(match):
            alt = match.group(1)
            src = match.group(2)
            if not alt:
                # Generate alt from filename
                filename = src.split('/')[-1].rsplit('.', 1)[0]
                alt = filename.replace('-', ' ').replace('_', ' ').title()
            return f'<img src="{src}" alt="{alt}" loading="lazy">'
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', img_with_alt, text)

        # Links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)

        # List items - collect consecutive lines
        lines = text.split('\n')
        processed = []
        list_items = []

        for line in lines:
            if line.strip().startswith('- '):
                list_items.append(f'<li>{line.strip()[2:]}</li>')
            else:
                if list_items:
                    processed.append('<ul>' + ''.join(list_items) + '</ul>')
                    list_items = []
                processed.append(line)
        if list_items:
            processed.append('<ul>' + ''.join(list_items) + '</ul>')

        text = '\n'.join(processed)

        # Paragraphs (simple)
        paragraphs = text.split('\n\n')
        result = []
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            # Skip wrapping HTML blocks in <p> tags
            if p.startswith(('<h', '<ul', '<img', '<div', '</div')):
                result.append(p)
            elif '<div' in p or '</div>' in p:
                result.append(p)
            else:
                result.append(f'<p>{p}</p>')

        return '\n'.join(result)

OUTPUT_DIR = Path("dist")
CONTENT_DIR = Path("content")

# HTML Template
BASE_TEMPLATE = '''<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Autolla Nepaliin</title>
    <meta name="description" content="{description}">
    <link rel="canonical" href="https://autollanepaliin.fi{canonical}">
    <!-- Open Graph -->
    <meta property="og:title" content="{title} - Autolla Nepaliin">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{og_image}">
    <meta property="og:url" content="https://autollanepaliin.fi{canonical}">
    <meta property="og:type" content="{og_type}">
    <meta property="og:site_name" content="Autolla Nepaliin">
    <meta property="og:locale" content="{og_locale}">
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title} - Autolla Nepaliin">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{og_image}">
    <!-- Hreflang -->
    <link rel="alternate" hreflang="fi" href="https://autollanepaliin.fi/">
    <link rel="alternate" hreflang="en" href="https://autollanepaliin.fi/in-english/">
    <link rel="alternate" hreflang="x-default" href="https://autollanepaliin.fi/">
    {extra_head}
    <style>
        :root {{
            --primary: #d4a853;
            --dark: #1a1a1a;
            --light: #f5f5f5;
            --text: #333;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html {{
            font-size: 16px;
            -webkit-text-size-adjust: 100%;
            -moz-text-size-adjust: 100%;
            text-size-adjust: 100%;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: var(--text);
            background: var(--light);
            font-size: 1rem;
        }}
        header {{
            background: var(--dark);
            color: white;
            padding: 1rem;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        header nav {{
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        header a {{
            color: var(--primary);
            text-decoration: none;
            font-weight: bold;
        }}
        header .logo {{ font-size: 1.5rem; }}
        header ul {{
            list-style: none;
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
        }}
        header ul a {{ color: white; font-weight: normal; }}
        header ul a:hover {{ color: var(--primary); }}
        main {{
            max-width: 800px;
            margin: 2rem auto;
            padding: 0 1rem;
        }}
        article {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        article h1 {{ color: var(--dark); margin-bottom: 0.5rem; }}
        article .meta {{
            color: #666;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
        }}
        article img {{
            display: block;
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            margin: 1rem 0;
            clear: both;
        }}
        article p {{ margin-bottom: 1rem; }}
        article h2, article h3 {{ margin: 1.5rem 0 0.75rem; color: var(--dark); }}
        article a {{ color: var(--primary); }}
        article ul, article ol {{ margin: 1rem 0 1rem 1.5rem; }}
        article li {{ margin-bottom: 0.5rem; }}
        article blockquote {{
            border-left: 4px solid var(--primary);
            padding-left: 1rem;
            margin: 1rem 0;
            font-style: italic;
            color: #555;
        }}
        .post-list {{
            list-style: none;
        }}
        .post-list li {{
            background: white;
            margin-bottom: 1rem;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .post-list h2 {{ margin: 0 0 0.5rem; font-size: 1.25rem; }}
        .post-list h2 a {{ color: var(--dark); text-decoration: none; }}
        .post-list h2 a:hover {{ color: var(--primary); }}
        .post-list .meta {{ color: #666; font-size: 0.85rem; }}
        .post-list .excerpt {{ color: #555; margin-top: 0.5rem; }}
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }}
        .card {{
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .card img {{
            width: 150px;
            height: 150px;
            object-fit: cover;
            border-radius: 50%;
            margin: 1rem auto;
            display: block;
        }}
        .card strong {{ font-size: 1.2rem; display: block; margin-bottom: 0.25rem; }}
        .card em {{ color: var(--primary); font-style: normal; }}
        .card em + em {{ color: #666; font-size: 0.9rem; }}
        .card em + em::before {{ content: " · "; color: #999; }}
        footer {{
            background: var(--dark);
            color: white;
            padding: 2rem 1rem;
            text-align: center;
            margin-top: 3rem;
        }}
        footer a {{ color: var(--primary); }}
        footer img {{ transition: filter 0.2s ease, opacity 0.2s ease; }}
        .pagination {{
            display: flex;
            justify-content: center;
            gap: 1rem;
            margin-top: 2rem;
        }}
        .pagination a {{
            background: var(--primary);
            color: var(--dark);
            padding: 0.5rem 1rem;
            border-radius: 4px;
            text-decoration: none;
            font-weight: bold;
        }}
        .hero {{
            background: var(--dark);
            color: white;
            padding: 4rem 1rem;
            text-align: center;
        }}
        .hero h1 {{ font-size: 2.5rem; margin-bottom: 1rem; }}
        .hero p {{ max-width: 600px; margin: 0 auto 2rem; opacity: 0.9; }}
        .hero .cta {{
            display: inline-block;
            background: var(--primary);
            color: var(--dark);
            padding: 1rem 2rem;
            border-radius: 4px;
            text-decoration: none;
            font-weight: bold;
            margin: 0 0.5rem;
        }}
        .video-container {{
            position: relative;
            margin: 2rem 0;
        }}
        .video-container:has(iframe) {{
            padding-bottom: 56.25%;
        }}
        .video-container iframe {{
            position: absolute;
            top: 0; left: 0;
            width: 100%; height: 100%;
            border: none;
            border-radius: 8px;
        }}
        .btn-secondary {{
            display: inline-block;
            background: linear-gradient(135deg, var(--dark) 0%, #2a2a2a 100%);
            color: white;
            padding: 1rem 2.5rem;
            border-radius: 50px;
            text-decoration: none;
            font-weight: 600;
            font-size: 1.1rem;
            letter-spacing: 0.5px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }}
        .btn-secondary:hover {{
            background: linear-gradient(135deg, #2a2a2a 0%, var(--dark) 100%);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
            border-color: var(--primary);
            color: var(--primary);
        }}
        .skip-link {{
            position: absolute;
            top: -40px;
            left: 0;
            background: var(--primary);
            color: var(--dark);
            padding: 8px 16px;
            z-index: 1000;
            text-decoration: none;
            font-weight: bold;
        }}
        .skip-link:focus {{ top: 0; }}
        .post-nav {{
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin-top: 2rem;
            padding-top: 1.5rem;
            border-top: 1px solid #eee;
        }}
        .post-nav a {{
            flex: 1;
            padding: 1rem;
            background: var(--light);
            border-radius: 8px;
            text-decoration: none;
            color: var(--text);
        }}
        .post-nav a:hover {{ background: #e8e8e8; }}
        .post-nav .prev {{ text-align: left; }}
        .post-nav .next {{ text-align: right; }}
        .post-nav .label {{ font-size: 0.8rem; color: #666; display: block; margin-bottom: 0.25rem; }}
        .reading-time {{ color: #888; font-size: 0.85rem; }}
        .categories {{ margin-top: 0.5rem; }}
        .categories a {{
            display: inline-block;
            background: var(--light);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-right: 0.5rem;
            margin-bottom: 0.25rem;
            text-decoration: none;
            color: var(--text);
        }}
        .categories a:hover {{ background: #e0e0e0; }}
        @media (max-width: 600px) {{
            header nav {{ flex-direction: column; text-align: center; }}
            header ul {{ justify-content: center; }}
            .hero h1 {{ font-size: 1.75rem; }}
            article {{ padding: 1rem; }}
            .post-nav {{ flex-direction: column; }}
        }}
    </style>
{structured_data}
</head>
<body>
    <a href="#main-content" class="skip-link">Skip to content</a>
    <header>
        <nav aria-label="Main navigation">
            <a href="/" class="logo"><img src="/assets/uploads/Autolla_Nepaliin_Unelmien_elokuva_colormod1-300x164.png" alt="Autolla Nepaliin" style="height: 58px; vertical-align: middle;"></a>
            <ul>
                <li><a href="/blogi/">Blogi</a></li>
                <li><a href="/mita/">Tarina</a></li>
                <li><a href="/elokuva/">Elokuva</a></li>
                <li><a href="/kauppa/">Kauppa</a></li>
                <li><a href="/tekijat/">Tekijät</a></li>
                <li><a href="/in-english/">In English</a></li>
            </ul>
        </nav>
    </header>
    {content}
    <footer>
        <p>Autolla Nepaliin - Unelmien projekti ja elokuva &copy; 2012-2026</p>
        <p>
            <a href="https://facebook.com/autollanepaliin">Facebook</a> |
            <a href="https://instagram.com/autollanepaliin">Instagram</a> |
            <a href="https://youtube.com/autollanepaliin">YouTube</a>
        </p>
        <div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid #444;">
            <p style="font-size: 0.9rem; opacity: 0.8; margin-bottom: 1rem;">Elokuvan projektista tekivät:</p>
            <div style="display: flex; justify-content: center; align-items: center; gap: 2rem; flex-wrap: wrap;">
                <a href="https://www.elicreative.fi/" target="_blank" rel="noopener nofollow">
                    <img src="/assets/uploads/ELI-logo-01-150x150.png" alt="Eli Creative" style="height: 50px; filter: brightness(0) invert(1);">
                </a>
                <a href="https://blacklionpictures.fi/" target="_blank" rel="noopener nofollow">
                    <img src="/assets/uploads/blacklion_pictures_logo_A3_72dpi_white-106x150.png" alt="Black Lion Pictures" style="height: 50px;">
                </a>
            </div>
        </div>

        <div style="margin-top: 1.5rem;">
            <p style="font-size: 0.9rem; opacity: 0.8; margin-bottom: 1rem;">Projektin mahdollistivat:</p>
            <div style="display: flex; justify-content: center; align-items: center; gap: 1.5rem; flex-wrap: wrap; max-width: 800px; margin: 0 auto;">
                <a href="https://www.dreamdo.com/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/logo-dreamdo.png" alt="Dreamdo" style="height: 35px; filter: brightness(0) invert(1); opacity: 0.8;"></a>
                <a href="https://kameratori.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/logo-kameratori.png" alt="Kameratori" style="height: 35px; filter: brightness(0) invert(1); opacity: 0.8;"></a>
                <a href="https://kuvastin.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/logo-kuvastin.png" alt="Kuvastin" style="height: 35px; filter: brightness(0) invert(1); opacity: 0.8;"></a>
                <a href="https://moses.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/logo-moses.png" alt="Moses" style="height: 35px; filter: brightness(0) invert(1); opacity: 0.8;"></a>
                <a href="https://narvik.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/logo-narvik.png" alt="Narvik" style="height: 35px; filter: brightness(0) invert(1); opacity: 0.8;"></a>
                <a href="https://vuokrakamera.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/vuokrakamera.png" alt="Vuokrakamera" style="height: 35px; filter: brightness(0) invert(1); opacity: 0.8;"></a>
                <a href="https://www.varusteleka.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/Varusteleka.png" alt="Varusteleka" style="height: 35px; filter: brightness(0) invert(1); opacity: 0.8;"></a>
                <a href="https://www.volkswagen.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/vvauto.png" alt="VV-Auto" style="height: 35px; filter: brightness(0) invert(1); opacity: 0.8;"></a>
            </div>
        </div>

        <div style="margin-top: 1.5rem; padding-top: 1rem;">
            <p style="font-size: 0.9rem; opacity: 0.8; margin-bottom: 1rem;">Meistä on kirjoitettu:</p>
            <div style="display: flex; justify-content: center; align-items: center; gap: 1.5rem; flex-wrap: wrap; max-width: 900px; margin: 0 auto;">
                <a href="https://yle.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/yle.png" alt="YLE" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://www.aamulehti.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/aamulehti.png" alt="Aamulehti" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://www.is.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/iltasanomat.png" alt="Ilta-Sanomat" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://www.radionova.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/radionova.png" alt="Radio Nova" style="height: 30px;"></a>
                <a href="https://www.tamperelainen.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/tamperelainen.png" alt="Tamperelainen" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://www.city.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/city.png" alt="City" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://madventures.tv/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/madventures.png" alt="Madventures" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://global.finland.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/globalfinland.png" alt="Global Finland" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://nuotta.com/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/nuotta.png" alt="Nuotta" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://www.kangasalansanomat.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/KangasalanSanomat.png" alt="Kangasalan Sanomat" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://www.seurakuntalainen.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/seurakuntalainen.png" alt="Seurakuntalainen" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://www.sipoonsanomat.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/sipoonsanomat.png" alt="Sipoon Sanomat" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://kosa.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/kosa.png" alt="Kosa" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
            </div>
        </div>

        <div style="margin-top: 1.5rem; padding-top: 1rem;">
            <p style="font-size: 0.9rem; opacity: 0.8; margin-bottom: 1rem;">Projektia tukivat mainoksilla:</p>
            <div style="display: flex; justify-content: center; align-items: center; gap: 1.5rem; flex-wrap: wrap; max-width: 900px; margin: 0 auto;">
                <a href="https://topshot.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/topshot.png" alt="Topshot" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://easydiili.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/easydiili.png" alt="Easydiili" style="height: 30px;"></a>
                <a href="https://jpj-wood.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/jpj.png" alt="JPJ" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://jjoy.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/jjoy.png" alt="JJoy" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://kuntokauppa.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/kuntokauppa.png" alt="Kuntokauppa" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://acaudit.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/acaudit.png" alt="AC Audit" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://www.ncell.axiata.com/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/ncell.png" alt="Ncell" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://prosper.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/prosper.png" alt="Prosper" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://tilatuote.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/tilatuote.png" alt="Tilatuote" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://www.foto-silmunen.fi/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/silmunen.png" alt="Silmunen" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
                <a href="https://imboys.com/" target="_blank" rel="noopener nofollow"><img src="/assets/uploads/imboys.png" alt="Imboys" style="height: 30px; filter: brightness(0) invert(1); opacity: 0.7;"></a>
            </div>
        </div>
    </footer>
</body>
</html>'''

def parse_frontmatter(content):
    """Parse YAML frontmatter from markdown file."""
    if not content.startswith('---'):
        return {}, content

    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content

    frontmatter = {}
    current_key = None
    lines = parts[1].strip().split('\n')

    for line in lines:
        # Check if this is a list item (starts with spaces and -)
        stripped = line.lstrip()
        if stripped.startswith('- '):
            if current_key:
                # Add to current list
                value = html.unescape(stripped[2:].strip().strip('"'))
                if current_key not in frontmatter:
                    frontmatter[current_key] = []
                if isinstance(frontmatter[current_key], list):
                    frontmatter[current_key].append(value)
        elif ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            # Check for JSON-style array
            if value.startswith('[') and value.endswith(']'):
                try:
                    frontmatter[key] = json.loads(value)
                except:
                    frontmatter[key] = html.unescape(value.strip('"'))
            elif value:
                frontmatter[key] = html.unescape(value.strip('"'))
            # If value is empty, might be a list header - don't set yet

    return frontmatter, parts[2].strip()

def process_embeds(html_content):
    """Convert embed shortcodes to iframes."""
    # YouTube embeds
    def youtube_embed(match):
        url = match.group(1)
        # Extract video ID
        video_id = None
        if 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]
        elif 'youtube.com/watch' in url:
            video_id = re.search(r'v=([^&]+)', url)
            if video_id:
                video_id = video_id.group(1)
        if video_id:
            return f'''<div class="video-container">
                <iframe src="https://www.youtube.com/embed/{video_id}" allowfullscreen></iframe>
            </div>'''
        return ''

    # Handle embed tags (may be wrapped in <p> tags)
    html_content = re.sub(r'(?:<p>)?\[embed\](.*?)\[/embed\](?:</p>)?', youtube_embed, html_content)
    # Handle hq-youtube-embed with regular or escaped quotes
    html_content = re.sub(r'\[hq-youtube-embed id=[\\"]?([^"\]\\]+)[\\"]?\]',
        lambda m: f'<div class="video-container"><iframe src="https://www.youtube.com/embed/{m.group(1)}" allowfullscreen></iframe></div>',
        html_content)

    return html_content

def process_card_grid(html_content):
    """Convert :::card markers to HTML grid layout."""
    # Convert card markers to divs - handle both wrapped in <p> and standalone
    html_content = re.sub(r'<p>:::card</p>', '<!--CARD_START-->', html_content)
    html_content = re.sub(r'<p>:::endcard</p>', '<!--CARD_END-->', html_content)
    html_content = re.sub(r':::card', '<!--CARD_START-->', html_content)
    html_content = re.sub(r':::endcard', '<!--CARD_END-->', html_content)

    # Find all card blocks and collect them
    card_pattern = r'<!--CARD_START-->(.*?)<!--CARD_END-->'
    cards = re.findall(card_pattern, html_content, flags=re.DOTALL)

    if cards:
        # Build the grid with all cards
        card_html = '<div class="card-grid">'
        for card_content in cards:
            # Clean up the card content - remove orphan <p> tags at start/end
            card_content = re.sub(r'^[\s\n]*<p>[\s\n]*', '', card_content)
            card_content = re.sub(r'[\s\n]*</p>[\s\n]*$', '', card_content)
            card_content = card_content.strip()
            card_html += f'<div class="card">{card_content}</div>'
        card_html += '</div>'

        # Replace all card blocks with the single grid
        # First, replace the first card block with the grid
        html_content = re.sub(card_pattern, '<!--CARD_PLACEHOLDER-->', html_content, count=1, flags=re.DOTALL)
        # Remove remaining card blocks
        html_content = re.sub(card_pattern, '', html_content, flags=re.DOTALL)
        # Insert the grid at the placeholder
        html_content = html_content.replace('<!--CARD_PLACEHOLDER-->', card_html)

        # Clean up empty paragraphs left behind
        html_content = re.sub(r'<p>\s*</p>', '', html_content)

    return html_content

def clean_shortcodes(content):
    """Remove WordPress shortcodes that can't be converted."""
    # Remove vc_row, vc_column, etc.
    content = re.sub(r'\[/?vc_\w+[^\]]*\]', '', content)
    content = re.sub(r'\[/?custom_headline[^\]]*\]', '', content)
    content = re.sub(r'\[/?text_output[^\]]*\]', '', content)
    content = re.sub(r'\[/?container[^\]]*\]', '', content)
    content = re.sub(r'\[/?counter[^\]]*\]', '', content)
    content = re.sub(r'\[/?button[^\]]*\]', '', content)
    content = re.sub(r'\[/?line[^\]]*\]', '', content)
    content = re.sub(r'\[/?icon[^\]]*\]', '', content)
    content = re.sub(r'\[ff[^\]]*\]', '', content)
    return content.strip()

def format_date(date_str, lang='fi'):
    """Format date for display."""
    if not date_str:
        return ''
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        if lang == 'en':
            months = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
            return f'{months[dt.month-1]} {dt.day}, {dt.year}'
        else:
            months = ['tammikuuta', 'helmikuuta', 'maaliskuuta', 'huhtikuuta',
                      'toukokuuta', 'kesäkuuta', 'heinäkuuta', 'elokuuta',
                      'syyskuuta', 'lokakuuta', 'marraskuuta', 'joulukuuta']
            return f'{dt.day}. {months[dt.month-1]} {dt.year}'
    except:
        return date_str


def get_post_language(slug):
    """Get language metadata from post markdown file."""
    md_files = list((CONTENT_DIR / 'posts').glob(f'*-{slug}.md'))
    if not md_files:
        md_files = list((CONTENT_DIR / 'posts').glob(f'{slug}.md'))
    if md_files:
        content = md_files[0].read_text(encoding='utf-8')
        meta, _ = parse_frontmatter(content)
        return meta.get('language', 'fi')
    return 'fi'

def clean_excerpt(text):
    """Clean markdown artifacts from excerpt for display in listings."""
    if not text:
        return ''
    # Remove markdown images ![alt](url)
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    # Remove markdown links but keep text [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove shortcodes [anything]
    text = re.sub(r'\[[^\]]+\]', '', text)
    # Remove heading markers #####
    text = re.sub(r'#{1,6}\s*', '', text)
    # Remove bold/italic markers (paired)
    text = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text)
    # Remove standalone asterisks
    text = re.sub(r'^\*+\s*', '', text)
    text = re.sub(r'\s*\*+$', '', text)
    # Remove :::card markers
    text = re.sub(r':::(?:card|endcard)', '', text)
    # Remove partial image syntax at end (truncated)
    text = re.sub(r'!\[[^\]]*$', '', text)  # ![incomplete
    text = re.sub(r'!\[[^\]]*\]\([^)]*$', '', text)  # ![alt](incomp
    text = re.sub(r'!\([^)]*$', '', text)  # !(incomplete
    # Remove escaped quotes
    text = text.replace('\\"', '"').replace("\\'", "'")
    text = text.replace('\\\"', '"')
    # Clean up excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def calculate_reading_time(text):
    """Calculate reading time in minutes based on word count."""
    words = len(re.findall(r'\w+', text))
    minutes = max(1, round(words / 200))  # ~200 words per minute
    return minutes

def generate_post_page(meta, content, output_path, prev_post=None, next_post=None):
    """Generate HTML page for a single post."""
    # Remove first image if it matches featured image (avoid duplication)
    featured_image = meta.get('featured_image', '')
    if featured_image:
        # Check if content starts with the same image
        first_img_match = re.match(r'^\s*!\[[^\]]*\]\(([^)]+)\)', content)
        if first_img_match:
            first_img_src = first_img_match.group(1)
            # Compare image paths (handle both with and without leading slash)
            if first_img_src.rstrip('/') == featured_image.rstrip('/') or \
               first_img_src.lstrip('/') == featured_image.lstrip('/'):
                # Remove the first image line
                content = re.sub(r'^\s*!\[[^\]]*\]\([^)]+\)\s*\n?', '', content, count=1)

    # Calculate reading time before converting to HTML
    reading_time = calculate_reading_time(content)

    html_content = md(content)
    html_content = process_embeds(html_content)
    html_content = process_card_grid(html_content)
    html_content = clean_shortcodes(html_content)

    featured_img = ''
    if meta.get('featured_image'):
        featured_img = f'<img src="{meta["featured_image"]}" alt="{html.escape(meta.get("title", ""))}" class="featured-image" style="width: 100%; max-height: 400px; object-fit: cover; border-radius: 8px; margin-bottom: 1.5rem;">'

    # Use language from metadata for date formatting
    lang = meta.get('language', 'fi')

    # Clean title (fix double spaces)
    title = re.sub(r'\s+', ' ', meta.get("title", "")).strip()

    # Reading time text
    reading_label = "min read" if lang == "en" else "min lukuaika"
    reading_html = f'<span class="reading-time"> · {reading_time} {reading_label}</span>'

    # Categories (hide generic ones)
    categories_html = ''
    categories = meta.get('categories', [])
    hidden_categories = {'text @en', 'photo', 'teksti', 'valokuva', 'text', 'video @en', 'video'}
    filtered_categories = [cat for cat in categories if cat.lower() not in hidden_categories]
    if filtered_categories:
        cat_links = ' '.join(f'<span style="background: var(--light); padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">{html.escape(cat)}</span>' for cat in filtered_categories)
        categories_html = f'<div class="categories" style="margin-top: 0.5rem;">{cat_links}</div>'

    # Prev/Next navigation
    post_nav = ''
    if prev_post or next_post:
        prev_label = "← Previous" if lang == "en" else "← Edellinen"
        next_label = "Next →" if lang == "en" else "Seuraava →"
        prev_html = ''
        next_html = ''
        if prev_post:
            prev_title = re.sub(r'\s+', ' ', prev_post.get('title', '')).strip()
            prev_html = f'<a href="/{prev_post.get("slug")}/" class="prev"><span class="label">{prev_label}</span>{html.escape(prev_title)}</a>'
        if next_post:
            next_title = re.sub(r'\s+', ' ', next_post.get('title', '')).strip()
            next_html = f'<a href="/{next_post.get("slug")}/" class="next"><span class="label">{next_label}</span>{html.escape(next_title)}</a>'
        post_nav = f'<nav class="post-nav" aria-label="Post navigation">{prev_html}{next_html}</nav>'

    # Author display (hide for specific pages)
    slug = meta.get('slug', '')
    hide_meta_pages = {'elokuva', 'tekijat', 'mita', 'in-english', 'kauppa', 'vaikutus'}

    author_data = meta.get('author', 'Juho Leppänen')
    if isinstance(author_data, list):
        author_text = ' & '.join(author_data)
    else:
        author_text = author_data

    if slug in hide_meta_pages:
        author_html = ''
        reading_html = ''
        meta_html = ''
    else:
        author_html = f' · {html.escape(author_text)}'
        meta_html = f'<div class="meta">{format_date(meta.get("date", ""), lang)}{author_html}{reading_html}</div>'

    page_content = f'''
    <main id="main-content">
        <article>
            {featured_img}
            <h1>{html.escape(title)}</h1>
            {meta_html}
            {categories_html}
            {html_content}
            {post_nav}
        </article>
    </main>
    '''

    # Clean description (fix double spaces)
    description = re.sub(r'\s+', ' ', meta.get('excerpt', meta.get('title', ''))).strip()[:160]

    # JSON-LD structured data for articles
    if isinstance(author_data, list):
        author_jsonld = [{"@type": "Person", "name": name} for name in author_data]
    else:
        author_jsonld = {"@type": "Person", "name": author_data}
    jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "datePublished": meta.get('date', ''),
        "author": author_jsonld,
        "publisher": {
            "@type": "Organization",
            "name": "Autolla Nepaliin",
            "url": "https://autollanepaliin.fi"
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"https://autollanepaliin.fi/{meta.get('slug', '')}/"
        }
    }
    if meta.get('featured_image'):
        jsonld["image"] = f"https://autollanepaliin.fi{meta.get('featured_image')}"
    if description:
        jsonld["description"] = description
    structured_data = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>'

    og_image = f"https://autollanepaliin.fi{meta.get('featured_image', '')}" if meta.get('featured_image') else "https://pub-e1f2ac35c79943dbb0fdba5cf836dbac.r2.dev/autollanepaliin-poster.jpg"

    page = BASE_TEMPLATE.format(
        title=html.escape(title),
        lang=lang,
        description=html.escape(description),
        canonical=f'/{meta.get("slug", "")}/',
        content=page_content,
        structured_data=structured_data,
        og_image=og_image,
        og_type='article',
        og_locale='fi_FI' if lang == 'fi' else 'en_US',
        extra_head=''
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding='utf-8')

def generate_blog_index(posts, page_num, total_pages, output_dir):
    """Generate blog index page with pagination."""
    posts_html = '<ul class="post-list">'
    for post in posts:
        excerpt = clean_excerpt(post.get('excerpt', ''))[:200]
        if excerpt:
            excerpt = excerpt.rstrip('.') + '...'
        # Format date for display
        date_str = post.get('date', '')
        if date_str and ' ' in date_str:
            date_str = date_str.split(' ')[0]  # Get just the date part
        # Featured image thumbnail
        thumb = ''
        if post.get('featured_image'):
            thumb = f'<img src="{post["featured_image"]}" alt="" style="width: 120px; height: 80px; object-fit: cover; border-radius: 4px; float: left; margin-right: 1rem;">'
        # Author
        author_data = post.get('author', 'Juho Leppänen')
        if isinstance(author_data, list):
            author_text = ' & '.join(author_data)
        else:
            author_text = author_data
        posts_html += f'''
        <li style="overflow: hidden;">
            {thumb}
            <h2><a href="/{post['slug']}/">{html.escape(post['title'])}</a></h2>
            <div class="meta">{format_date(date_str)} · {html.escape(author_text)}</div>
            <div class="excerpt">{html.escape(excerpt)}</div>
        </li>
        '''
    posts_html += '</ul>'

    # Pagination
    pagination = '<div class="pagination">'
    if page_num > 1:
        prev_page = '/blogi/' if page_num == 2 else f'/blogi/sivu/{page_num - 1}/'
        pagination += f'<a href="{prev_page}">&laquo; Uudemmat</a>'
    if page_num < total_pages:
        pagination += f'<a href="/blogi/sivu/{page_num + 1}/">Vanhemmat &raquo;</a>'
    pagination += '</div>'

    page_content = f'''
    <main id="main-content">
        <h1 style="margin-bottom: 1.5rem;">Blogi</h1>
        <div style="margin-bottom: 1.5rem;">{pagination}</div>
        {posts_html}
        {pagination}
    </main>
    '''

    page = BASE_TEMPLATE.format(
        title=f'Blogi{" - Sivu " + str(page_num) if page_num > 1 else ""}',
        lang='fi',
        description='Autolla Nepaliin matkakertomus ja päiväkirja. Seuraa viiden ystävän seikkailua Suomesta Nepaliin.',
        canonical=f'/blogi/{"sivu/" + str(page_num) + "/" if page_num > 1 else ""}',
        content=page_content,
        structured_data='',
        og_image='https://pub-e1f2ac35c79943dbb0fdba5cf836dbac.r2.dev/autollanepaliin-poster.jpg',
        og_type='website',
        og_locale='fi_FI',
        extra_head=''
    )

    if page_num == 1:
        output_path = output_dir / 'blogi' / 'index.html'
    else:
        output_path = output_dir / 'blogi' / 'sivu' / str(page_num) / 'index.html'

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding='utf-8')

def generate_travel_diary_page(posts, output_dir):
    """Generate travel diary page with posts in chronological order (oldest first)."""
    # Filter posts: travel diary ends with paatosjuhla-16-12 (2012-12-02)
    TRAVEL_DIARY_END_DATE = '2012-12-02'
    diary_posts = [p for p in posts if p.get('date', '')[:10] <= TRAVEL_DIARY_END_DATE]

    # Reverse the posts to show oldest first (chronological order)
    chronological_posts = list(reversed(diary_posts))

    posts_html = '<ul class="post-list">'
    for post in chronological_posts:
        excerpt = clean_excerpt(post.get('excerpt', ''))[:200]
        if excerpt:
            excerpt = excerpt.rstrip('.') + '...'
        date_str = post.get('date', '')
        if date_str and ' ' in date_str:
            date_str = date_str.split(' ')[0]
        thumb = ''
        if post.get('featured_image'):
            thumb = f'<img src="{post["featured_image"]}" alt="" style="width: 120px; height: 80px; object-fit: cover; border-radius: 4px; float: left; margin-right: 1rem;">'
        # Author
        post_author = post.get('author', 'Juho Leppänen')
        if isinstance(post_author, list):
            post_author_text = ' & '.join(post_author)
        else:
            post_author_text = post_author
        posts_html += f'''
        <li style="overflow: hidden;">
            {thumb}
            <h2><a href="/{post['slug']}/">{html.escape(post['title'])}</a></h2>
            <div class="meta">{format_date(date_str)} · {html.escape(post_author_text)}</div>
            <div class="excerpt">{html.escape(excerpt)}</div>
        </li>
        '''
    posts_html += '</ul>'

    page_content = f'''
    <main id="main-content">
        <article style="margin-bottom: 2rem;">
            <h1>Matkapäiväkirja</h1>
            <p>Tämä on Autolla Nepaliin -matkan päiväkirja aikajärjestyksessä. Kirjoitukset on järjestetty vanhimmasta uusimpaan, jotta voit seurata tarinaa alusta loppuun.</p>
        </article>
        {posts_html}
        <div class="pagination" style="margin-top: 2rem;">
            <a href="/blogi/">Lue mitä tapahtui seuraavaksi blogista &rarr;</a>
        </div>
    </main>
    '''

    page = BASE_TEMPLATE.format(
        title='Matkapäiväkirja',
        lang='fi',
        description='Autolla Nepaliin matkapäiväkirja aikajärjestyksessä - lue tarina alusta loppuun.',
        canonical='/matkapaivakirja/',
        content=page_content,
        structured_data='',
        og_image='https://pub-e1f2ac35c79943dbb0fdba5cf836dbac.r2.dev/autollanepaliin-poster.jpg',
        og_type='website',
        og_locale='fi_FI',
        extra_head=''
    )

    output_path = output_dir / 'matkapaivakirja' / 'index.html'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding='utf-8')


def generate_english_page(posts, output_dir):
    """Generate In English page with English posts listing."""
    # Read the In English page content
    in_english_md = CONTENT_DIR / 'pages' / 'in-english.md'
    if in_english_md.exists():
        content = in_english_md.read_text(encoding='utf-8')
        meta, body = parse_frontmatter(content)
        intro_html = md(body)
        intro_html = clean_shortcodes(intro_html)
    else:
        intro_html = '<h2>In English</h2>'

    # Reverse posts for chronological order (oldest first)
    chronological_posts = list(reversed(posts))

    # Generate posts list with Blog Posts heading
    posts_html = '<h2 style="margin: 2rem 0 1rem;">Blog Posts</h2>'
    posts_html += '<p style="margin-bottom: 1.5rem; color: #666;">Posts are in reverse chronological order, oldest first, so you can follow the story from the beginning.</p>'
    posts_html += '<ul class="post-list">'
    for post in chronological_posts:
        excerpt = clean_excerpt(post.get('excerpt', ''))[:200]
        if excerpt:
            excerpt = excerpt.rstrip('.') + '...'
        date_str = post.get('date', '')
        if date_str and ' ' in date_str:
            date_str = date_str.split(' ')[0]
        thumb = ''
        if post.get('featured_image'):
            thumb = f'<img src="{post["featured_image"]}" alt="" style="width: 120px; height: 80px; object-fit: cover; border-radius: 4px; float: left; margin-right: 1rem;">'
        # Author
        en_author = post.get('author', 'Juho Leppänen')
        if isinstance(en_author, list):
            en_author_text = ' & '.join(en_author)
        else:
            en_author_text = en_author
        posts_html += f'''
        <li style="overflow: hidden;">
            {thumb}
            <h2><a href="/{post['slug']}/">{html.escape(post['title'])}</a></h2>
            <div class="meta">{format_date(date_str, 'en')} · {html.escape(en_author_text)}</div>
            <div class="excerpt">{html.escape(excerpt)}</div>
        </li>
        '''
    posts_html += '</ul>'

    page_content = f'''
    <main id="main-content">
        <article>
            {intro_html}
        </article>
        {posts_html}
    </main>
    '''

    page = BASE_TEMPLATE.format(
        title='In English',
        lang='en',
        description='Watch Driving to Nepal free - Finland\'s first crowdfunded documentary. 5 friends, 20,000km, 2 schools built in Nepal.',
        canonical='/in-english/',
        content=page_content,
        structured_data='',
        og_image='https://pub-e1f2ac35c79943dbb0fdba5cf836dbac.r2.dev/autollanepaliin-poster.jpg',
        og_type='video.movie',
        og_locale='en_US',
        extra_head=''
    )

    output_path = output_dir / 'in-english' / 'index.html'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding='utf-8')


def generate_home_page(posts, output_dir):
    """Generate home page."""
    # Latest 5 posts
    recent_posts = '<ul class="post-list">'
    for post in posts[:5]:
        thumb = ''
        if post.get('featured_image'):
            thumb = f'<img src="{post["featured_image"]}" alt="" style="width: 120px; height: 80px; object-fit: cover; border-radius: 4px; float: left; margin-right: 1rem;">'
        # Author
        home_author = post.get('author', 'Juho Leppänen')
        if isinstance(home_author, list):
            home_author_text = ' & '.join(home_author)
        else:
            home_author_text = home_author
        # Excerpt
        excerpt = clean_excerpt(post.get('excerpt', ''))[:200]
        if excerpt:
            excerpt = excerpt.rstrip('.') + '...'
        excerpt_html = f'<div class="excerpt">{html.escape(excerpt)}</div>' if excerpt else ''
        recent_posts += f'''
        <li style="overflow: hidden;">
            {thumb}
            <h2><a href="/{post['slug']}/">{html.escape(post['title'])}</a></h2>
            <div class="meta">{format_date(post.get('date', ''))} · {html.escape(home_author_text)}</div>
            {excerpt_html}
        </li>
        '''
    recent_posts += '</ul>'

    page_content = f'''
    <div class="hero">
        <h1>Autolla Nepaliin</h1>
        <p>Viiden suomalaisen seikkailu Nepaliin ja takaisin, hyvän asian puolesta.</p>
        <h3 style="margin-top: 2rem;">Katso traileri</h3>
        <video controls width="100%" style="max-width: 800px; display: block; margin: 1rem auto 2rem; aspect-ratio: 16/9;" poster="https://pub-e1f2ac35c79943dbb0fdba5cf836dbac.r2.dev/autollanepaliin-poster.jpg">
            <source src="https://pub-e1f2ac35c79943dbb0fdba5cf836dbac.r2.dev/autollanepaliin-traileri.webm" type="video/webm">
            Your browser does not support the video tag.
        </video>
        <a href="/matkapaivakirja/" class="cta">Lue matkapäiväkirja</a>
        <a href="/elokuva/" class="cta">Katso elokuva ilmaiseksi</a>
    </div>
    <main id="main-content">
        <article>
            <h2>Tarina lyhyesti</h2>
            <p>Juholla on unelma oikeudenmukaisemmasta maailmasta. Tehdessään töitä Aasiassa erityisesti kastittomien huonot olot Nepalissa ovat jääneet hänen mieleensä. Juho haluaa löytää tavan auttaa heitä.</p>
            <p>Unelmasta kasvaa suurempi, kun Juhon ystävät liittyvät mukaan projektiin ja he lähtevät pakettiautolla matkalle Nepaliin tavoitteenaan saada huomiota kastittomien oloille ja erityisesti paikalliselle naisten turvakodille.</p>
            <p>Kaikkien mutkien jälkeen projekti onnistui, lue lisää <a href="/tiivistelma-autolla-nepaliin-tuloksista-10-vuotta-ja-risat/">täältä</a> tai lue <a href="/kauppa/">kauppa</a>-sivulta miten voit ostaa Nepalissa tehtyjä koruja nepalilaisten auttamiseksi.</p>
            <blockquote style="border-left: 4px solid var(--primary); padding-left: 1.5rem; margin: 1.5rem 0; font-style: italic; color: #555;">
                <p>"Nuorten unelmoinnilla pitää olla aina tilaa, sitä pitää aina pystyä kannustamaan ja mahdollistamaan."</p>
                <cite style="font-style: normal; font-size: 0.9rem; display: block; margin-top: 0.5rem;">— Juho Leppänen</cite>
            </blockquote>
        </article>
        <h2 style="margin: 2rem 0 1rem;">Viimeisimmät kirjoitukset</h2>
        {recent_posts}
        <div class="pagination" style="margin-top: 2rem;">
            <a href="/blogi/">Kaikki kirjoitukset &rarr;</a>
        </div>
    </main>
    '''

    # JSON-LD for homepage
    home_jsonld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "name": "Autolla Nepaliin",
                "url": "https://autollanepaliin.fi",
                "description": "5 ystävää, 20 000 km, 2 koulua Nepaliin. Suomen ensimmäinen joukkorahoitettu dokumenttielokuva.",
                "foundingDate": "2012",
                "sameAs": [
                    "https://www.imdb.com/title/tt4103474/"
                ]
            },
            {
                "@type": "VideoObject",
                "name": "Autolla Nepaliin - Traileri",
                "description": "Traileri dokumenttielokuvasta Autolla Nepaliin - Unelmien elokuva",
                "thumbnailUrl": "https://pub-e1f2ac35c79943dbb0fdba5cf836dbac.r2.dev/autollanepaliin-poster.jpg",
                "uploadDate": "2014-01-01",
                "contentUrl": "https://www.youtube.com/watch?v=TnGl01FkMMo"
            }
        ]
    }, ensure_ascii=False)

    page = BASE_TEMPLATE.format(
        title='Etusivu',
        lang='fi',
        description='5 ystävää, 20 000 km, 1 unelma. Katso Suomen ensimmäinen joukkorahoitettu elokuva uskomattomasta seikkailusta hyvän asian puolesta.',
        canonical='/',
        content=page_content,
        structured_data=f'<script type="application/ld+json">{home_jsonld}</script>',
        og_image='https://pub-e1f2ac35c79943dbb0fdba5cf836dbac.r2.dev/autollanepaliin-poster.jpg',
        og_type='website',
        og_locale='fi_FI',
        extra_head=''
    )

    output_path = output_dir / 'index.html'
    output_path.write_text(page, encoding='utf-8')

def generate_rss_feed(posts, output_dir):
    """Generate RSS feed for the site."""
    from datetime import datetime

    # Get latest 20 posts
    recent_posts = posts[:20]

    # Build date for feed
    if recent_posts and recent_posts[0].get('date'):
        last_build = recent_posts[0]['date'].split(' ')[0]
    else:
        last_build = datetime.now().strftime('%Y-%m-%d')

    items = ''
    for post in recent_posts:
        title = html.escape(post.get('title', ''))
        slug = post.get('slug', '')
        link = f'https://autollanepaliin.fi/{slug}/'

        # Clean excerpt for description
        excerpt = clean_excerpt(post.get('excerpt', ''))[:300]
        if excerpt:
            excerpt = excerpt.rstrip('.') + '...'
        description = html.escape(excerpt)

        # Format date as RFC 822
        date_str = post.get('date', '')
        if date_str:
            try:
                if ' ' in date_str:
                    dt = datetime.strptime(date_str.split(' ')[0], '%Y-%m-%d')
                else:
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                pub_date = dt.strftime('%a, %d %b %Y 00:00:00 +0000')
            except:
                pub_date = ''
        else:
            pub_date = ''

        items += f'''    <item>
      <title>{title}</title>
      <link>{link}</link>
      <description>{description}</description>
      <pubDate>{pub_date}</pubDate>
      <guid>{link}</guid>
    </item>
'''

    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Autolla Nepaliin</title>
    <link>https://autollanepaliin.fi/</link>
    <description>Autolla Nepaliin - Viiden suomalaisen seikkailu Nepaliin ja takaisin</description>
    <language>fi</language>
    <lastBuildDate>{last_build}</lastBuildDate>
    <atom:link href="https://autollanepaliin.fi/feed.xml" rel="self" type="application/rss+xml"/>
{items}  </channel>
</rss>'''

    # Write RSS feed to root
    (output_dir / 'feed.xml').write_text(rss, encoding='utf-8')

def generate_sitemap(posts, pages, output_dir):
    """Generate sitemap.xml for the site."""
    from datetime import datetime

    urls = []

    # Homepage - highest priority
    urls.append(('https://autollanepaliin.fi/', '1.0', 'weekly'))

    # Main pages
    main_pages = ['in-english', 'elokuva', 'mita', 'kauppa', 'tekijat', 'blogi', 'matkapaivakirja', 'vaikutus']
    for slug in main_pages:
        urls.append((f'https://autollanepaliin.fi/{slug}/', '0.8', 'monthly'))

    # All posts
    for post in posts:
        slug = post.get('slug', '')
        if slug:
            urls.append((f'https://autollanepaliin.fi/{slug}/', '0.6', 'yearly'))

    # All pages
    for page in pages:
        slug = page.get('slug', '')
        if slug and slug not in main_pages:
            urls.append((f'https://autollanepaliin.fi/{slug}/', '0.5', 'yearly'))

    xml_urls = ''
    for url, priority, changefreq in urls:
        xml_urls += f'''  <url>
    <loc>{url}</loc>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>
'''

    sitemap = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_urls}</urlset>'''

    (output_dir / 'sitemap.xml').write_text(sitemap, encoding='utf-8')

def generate_llms_txt(output_dir):
    """Generate llms.txt for LLM consumption."""
    llms_content = '''# Autolla Nepaliin - Driving to Nepal

> 5 friends, 20,000 km, 1 dream: Finland's first 100% crowdfunded documentary that built 2 schools in Nepal.

## What is this?

Autolla Nepaliin (Driving to Nepal) is a Finnish documentary film and charity project. In 2012, five Finnish friends drove from Finland to Nepal in a 1989 Volkswagen Transporter van nicknamed "Möhköfantti" (Heffalump). Their 20,000 km journey through Russia, Kazakhstan, Kyrgyzstan, China, Pakistan, and India became Finland's first entirely crowdfunded documentary film.

## Key Facts

- **Journey**: 20,000 km from Finland to Nepal and back (2012)
- **Vehicle**: 1989 VW Transporter T3 nicknamed "Möhköfantti"
- **Route**: Finland → Russia → Kazakhstan → Kyrgyzstan → China → Pakistan → India → Nepal
- **Documentary**: "Autolla Nepaliin - Unelmien elokuva" (2014)
- **Funding**: First 100% crowdfunded Finnish film
- **Award**: Won Audience Jussi (Finnish Oscar) in 2015
- **IMDB**: https://www.imdb.com/title/tt4103474/

## Impact in Nepal

The project has had lasting impact:
- **15+ school buildings** constructed
- **80+ schools** supported in total
- **27,000 children** reached annually (as of 2021)
- **Girls' enrollment** increased from 25% to over 50%
- Schools registered as government schools (sustainable funding)
- **€134,770+** donated through jewelry sales by 2025

## The Cause

The mission was to help Dalit (untouchable caste) children get education and support women at Princess Beads shelter who escaped domestic violence. The women make handcrafted jewelry, which is sold to fund their education and livelihood.

## Store of Hope → Kaiko Clothing

The jewelry shop "Store of Hope" was founded in 2012. In 2020 it merged with Finnish brand Kaiko Clothing, which continues selling Nepalese jewelry with 7% of profits going to Nepal.

## Why This Story Matters

This project demonstrates:
1. **Young people can change the world** - Started by friends in their 20s with no film experience
2. **Dreams become reality** through persistence and community support
3. **Sustainable charity** - Created lasting infrastructure, not just one-time aid
4. **Crowdfunding power** - Proved community funding can produce professional films
5. **Adventure with purpose** - Combined personal challenge with meaningful impact

## Quotable

"Nuorten unelmoinnilla pitää olla aina tilaa, sitä pitää aina pystyä kannustamaan ja mahdollistamaan."
("There must always be room for young people's dreams; we must always be able to encourage and enable them.")
— Juho Leppänen, project founder

## Watch Free

The full documentary with English subtitles is available free at:
https://autollanepaliin.fi/in-english/

## Links

- Website: https://autollanepaliin.fi
- English page: https://autollanepaliin.fi/in-english/
- IMDB: https://www.imdb.com/title/tt4103474/
- Jewelry shop: https://kaikoclothing.com/collections/jewelry

## Contact

For media inquiries: lahjoita-tietokone@autollanepaliin.fi
'''

    (output_dir / 'llms.txt').write_text(llms_content, encoding='utf-8')

def generate_robots_txt(output_dir):
    """Generate robots.txt with sitemap reference."""
    robots_content = '''User-agent: *
Allow: /

Sitemap: https://autollanepaliin.fi/sitemap.xml
'''
    (output_dir / 'robots.txt').write_text(robots_content, encoding='utf-8')

def main():
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load content index and decode HTML entities
    with open(CONTENT_DIR / 'index.json', 'r', encoding='utf-8') as f:
        index = json.load(f)

    # Decode HTML entities in all string fields
    def decode_entities(obj):
        if isinstance(obj, str):
            return html.unescape(obj)
        elif isinstance(obj, dict):
            return {k: decode_entities(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [decode_entities(item) for item in obj]
        return obj

    posts = decode_entities(index['posts'])
    pages = decode_entities(index['pages'])

    # Separate posts by language
    finnish_posts = []
    english_posts = []
    for post in posts:
        lang = get_post_language(post['slug'])
        if lang == 'en':
            english_posts.append(post)
        else:
            finnish_posts.append(post)

    print(f"Found {len(finnish_posts)} Finnish posts, {len(english_posts)} English posts")
    print(f"Generating {len(posts)} post pages...")

    # Sort posts by date for prev/next navigation (oldest first for chronological nav)
    finnish_sorted = sorted(finnish_posts, key=lambda x: x.get('date', ''))
    english_sorted = sorted(english_posts, key=lambda x: x.get('date', ''))

    # Generate individual post pages with prev/next navigation
    for post in posts:
        slug = post['slug']
        lang = get_post_language(slug)

        # Find prev/next in same language
        sorted_list = english_sorted if lang == 'en' else finnish_sorted
        idx = next((i for i, p in enumerate(sorted_list) if p['slug'] == slug), -1)
        prev_post = sorted_list[idx - 1] if idx > 0 else None
        next_post = sorted_list[idx + 1] if idx >= 0 and idx < len(sorted_list) - 1 else None

        # Find the markdown file
        md_files = list((CONTENT_DIR / 'posts').glob(f'*-{slug}.md'))
        if not md_files:
            md_files = list((CONTENT_DIR / 'posts').glob(f'{slug}.md'))
        if md_files:
            content = md_files[0].read_text(encoding='utf-8')
            meta, body = parse_frontmatter(content)
            output_path = OUTPUT_DIR / slug / 'index.html'
            generate_post_page(meta, body, output_path, prev_post, next_post)

    print(f"Generating {len(pages)} page pages...")

    # Generate individual pages (skip in-english, it's handled separately)
    for page in pages:
        slug = page['slug']
        if slug == 'in-english':
            continue  # Skip, handled by generate_english_page
        md_file = CONTENT_DIR / 'pages' / f'{slug}.md'
        if md_file.exists():
            content = md_file.read_text(encoding='utf-8')
            meta, body = parse_frontmatter(content)
            # Clean shortcodes from body
            body = clean_shortcodes(body)
            output_path = OUTPUT_DIR / slug / 'index.html'
            generate_post_page(meta, body, output_path)

    # Generate blog index with pagination (Finnish posts only)
    POSTS_PER_PAGE = 20
    total_pages = (len(finnish_posts) + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE

    print(f"Generating {total_pages} blog index pages (Finnish only)...")

    for page_num in range(1, total_pages + 1):
        start = (page_num - 1) * POSTS_PER_PAGE
        end = start + POSTS_PER_PAGE
        page_posts = finnish_posts[start:end]
        generate_blog_index(page_posts, page_num, total_pages, OUTPUT_DIR)

    # Generate English page
    print("Generating In English page...")
    generate_english_page(english_posts, OUTPUT_DIR)

    # Generate travel diary page (chronological order)
    print("Generating travel diary page...")
    generate_travel_diary_page(finnish_posts, OUTPUT_DIR)

    # Generate home page (Finnish posts only for recent)
    print("Generating home page...")
    generate_home_page(finnish_posts, OUTPUT_DIR)

    # Generate RSS feed
    print("Generating RSS feed...")
    generate_rss_feed(posts, OUTPUT_DIR)

    # Generate sitemap
    print("Generating sitemap...")
    generate_sitemap(posts, pages, OUTPUT_DIR)

    # Generate llms.txt
    print("Generating llms.txt...")
    generate_llms_txt(OUTPUT_DIR)

    # Generate robots.txt
    print("Generating robots.txt...")
    generate_robots_txt(OUTPUT_DIR)

    # Generate 404 page
    page_404 = BASE_TEMPLATE.format(
        title='404 - Sivua ei löydy',
        lang='fi',
        description='Sivua ei löydy',
        canonical='/404.html',
        content='''
        <main id="main-content">
            <article style="text-align: center;">
                <h1>404 - Sivua ei löydy</h1>
                <p>Etsimääsi sivua ei valitettavasti löytynyt.</p>
                <p><a href="/">Palaa etusivulle</a></p>
            </article>
        </main>
        ''',
        structured_data='',
        og_image='https://pub-e1f2ac35c79943dbb0fdba5cf836dbac.r2.dev/autollanepaliin-poster.jpg',
        og_type='website',
        og_locale='fi_FI',
        extra_head=''
    )
    (OUTPUT_DIR / '404.html').write_text(page_404, encoding='utf-8')

    # Generate Cloudflare _redirects for old image URLs
    redirects = """# Redirect old WordPress image paths to new location
/wp-content/uploads/*.jpg /assets/uploads/:splat.webp 301
/wp-content/uploads/*.jpeg /assets/uploads/:splat.webp 301
/wp-content/uploads/*.png /assets/uploads/:splat.webp 301
/wp-content/uploads/*.gif /assets/uploads/:splat.webp 301
/wordpress/wp-content/uploads/*.jpg /assets/uploads/:splat.webp 301
/wordpress/wp-content/uploads/*.jpeg /assets/uploads/:splat.webp 301
/wordpress/wp-content/uploads/*.png /assets/uploads/:splat.webp 301
/wordpress/wp-content/uploads/*.gif /assets/uploads/:splat.webp 301

# Redirect old image formats to WebP (for /assets/uploads/)
/assets/uploads/*.jpg /assets/uploads/:splat.webp 301
/assets/uploads/*.jpeg /assets/uploads/:splat.webp 301
/assets/uploads/*.png /assets/uploads/:splat.webp 301

# Redirect accented URLs to ASCII versions
/matkapäiväkirja/ /matkapaivakirja/ 301
/tekijät/ /tekijat/ 301

# Redirect old WordPress API
/wp-json/* / 301

# RSS feed redirect
/feed/ /feed.xml 301
/feed /feed.xml 301
"""
    (OUTPUT_DIR / '_redirects').write_text(redirects, encoding='utf-8')

    # Generate Cloudflare Function for image redirects
    functions_dir = OUTPUT_DIR / 'functions' / 'assets' / 'uploads'
    functions_dir.mkdir(parents=True, exist_ok=True)
    function_code = """// Redirect old image formats to WebP
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const path = url.pathname;

  // Check if requesting old image format
  const match = path.match(/^\\/assets\\/uploads\\/(.+)\\.(jpg|jpeg|png)$/i);

  if (match) {
    const webpPath = '/assets/uploads/' + match[1] + '.webp';
    return Response.redirect(new URL(webpPath, url.origin), 301);
  }

  // Pass through to static assets
  return context.next();
}
"""
    (functions_dir / '[[path]].js').write_text(function_code, encoding='utf-8')

    # Copy assets if not already there
    assets_src = OUTPUT_DIR / 'assets'
    if assets_src.exists():
        print(f"Assets already in place at {assets_src}")

    print(f"\n✓ Site generated in {OUTPUT_DIR}")
    print(f"  - {len(posts)} blog posts ({len(finnish_posts)} Finnish, {len(english_posts)} English)")
    print(f"  - {len(pages)} pages")
    print(f"  - {total_pages} blog index pages (Finnish)")
    print(f"  - In English page with {len(english_posts)} posts")
    diary_count = len([p for p in finnish_posts if p.get('date', '')[:10] <= '2012-12-02'])
    print(f"  - Matkapäiväkirja page with {diary_count} posts (chronological)")
    print(f"  - Home page and 404 page")

if __name__ == '__main__':
    main()
