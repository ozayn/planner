# Image Optimization Standard

A short maintainer standard for all future image additions to the Planner.

## Core Rules

1. **External images** must go through the shared proxy/optimized path (`/api/image-proxy` or `ensure_loadable_image_url()` in `scripts/utils.py`). Do not serve raw external URLs directly in cards or lists.

2. **Uploads** must be resized on save. Do not store large originals without resizing.

3. **Do not serve large raw originals** by default in cards or lists. Use appropriately sized variants.

## Recommended Size Targets

| Context | Max Width | Use Case |
|---------|-----------|----------|
| Thumb | 200px | Thumbnails, discovery lists |
| Card | 400px | Event/venue cards |
| Detail | 600px | Detail views, modals |
| Large | 800px | Full-size display |

## Requirements for New Additions

Any new scrapers, URL import flows, or upload flows must either:

- **Omit images**, or
- **Use the shared optimized image path** (e.g. `ensure_loadable_image_url()` before saving, or rely on `create_events_in_database` which applies it automatically)

## Applies To

- New scrapers
- URL import / event extraction from URLs
- New upload flows
- Any new feature that displays or stores images on the website

## Reference

- Proxy: `/api/image-proxy?url=...&w=N`
- Utility: `scripts.utils.ensure_loadable_image_url(url, max_width=N)`
- Handler: `scripts.event_database_handler.create_events_in_database` applies optimization to event `image_url` automatically
