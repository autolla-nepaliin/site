# Autolla Nepaliin - Static Site

Static site for autollanepaliin.fi, generated from WordPress backup.

## Generate site

```bash
python3 generate_html.py
```

Output goes to `dist/` folder.

## Local development

```bash
cd dist && python3 -m http.server 8080
```

## Deploy to Cloudflare Pages

Uses Juho's Cloudflare account. Credentials in shared Apple Passwords group (Onni & Juho have access).

```bash
# Login (if needed, or to switch accounts)
npx wrangler logout
npx wrangler login

# Deploy
npx wrangler pages deploy dist --project-name=autollanepaliin
```
