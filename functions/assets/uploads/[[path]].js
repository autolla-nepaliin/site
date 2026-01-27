// Redirect old image formats to WebP
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const path = url.pathname;
  
  // Check if requesting old image format
  const match = path.match(/^(\/assets\/uploads\/.+)\.(jpg|jpeg|png|JPG|JPEG|PNG)$/);
  
  if (match) {
    const webpPath = match[1] + '.webp';
    return Response.redirect(new URL(webpPath, url.origin), 301);
  }
  
  // Pass through to static assets
  return context.next();
}
