# Autolla Nepaliin Static Site

## Project Overview
Static site converted from WordPress backup (.wpress format from All-in-One WP Migration plugin).

## Build Commands
```bash
# Extract content from WordPress and convert to markdown
python3 build_static_site.py

# Generate static HTML from markdown
python3 generate_html.py

# Run local server
npx serve dist -p 8080
```

## Content Rules

### Featured Images
- Use post's featured_image if available
- Fallback to first image in content if no featured_image
- Images displayed as thumbnails in blog listings

### WordPress Shortcodes
- `[column size="..."]...[/column]` → converted to card grid layout with `:::card`/`:::endcard` markers
- `[caption]...[/caption]` → markdown image with caption
- `[embed]...[/embed]` → YouTube iframe
- `[hq-youtube-embed id="..."]` → YouTube iframe (handles escaped quotes)

### URL Conversion
WordPress URLs converted to static paths:
- `https://autollanepaliin.fi/wordpress/wp-content/uploads/` → `/assets/uploads/`
- `https://autollanepaliin.fi/wp-content/uploads/` → `/assets/uploads/`
- `/wordpress/wp-content/uploads/` → `/assets/uploads/`
- `/wp-content/uploads/` → `/assets/uploads/`

### Card Grid (Team Members)
- Column shortcodes converted to CSS grid cards
- List markers (`- `) stripped from card content
- `email` → `Email:`, `www` → `Web:` labels added

## File Structure
```
content/
  posts/       # Markdown blog posts with frontmatter
  pages/       # Markdown pages
  index.json   # Content index for listings
dist/
  assets/uploads/  # Media files from WordPress
  [slug]/index.html  # Generated pages
```

## Testing Checklist
After rebuilding the site, verify:
- [ ] `/tekijat/` page shows team members in a 2-column grid with photos
- [ ] `/blogi/` listing shows clean excerpts (no markdown artifacts like `#####`, `![]()`]
- [ ] `/blogi/` posts have thumbnail images where available
- [ ] Footer sponsor/media logos are clickable and link to correct websites
- [ ] YouTube embeds work on posts and front page

## Deployment
Configured for Cloudflare Pages via `wrangler.toml`.
