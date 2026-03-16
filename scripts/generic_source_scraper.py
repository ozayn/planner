#!/usr/bin/env python3
"""
Generic source scraper: fetch a listing page and pass HTML to a source-specific extractor.
Returns normalized event dicts in the repository's expected event shape.
"""

import logging
from typing import Callable, List, Optional
from urllib.parse import urljoin, urlparse

from scripts.scraper_utils import create_scraper_session

logger = logging.getLogger(__name__)

# Extractor signature: (html: str, base_url: str) -> List[dict]
ExtractorFn = Callable[[str, str], List[dict]]


def scrape_source_listing(
    url: str,
    extractor: ExtractorFn,
    base_url: Optional[str] = None,
    use_cloudscraper: bool = False,
    timeout: int = 20,
) -> List[dict]:
    """
    Fetch a listing page and extract events using a source-specific extractor.

    Args:
        url: URL of the listing page.
        extractor: Function (html, base_url) -> list of event dicts.
        base_url: Base URL for resolving relative links. Defaults to url.
        use_cloudscraper: If True, try cloudscraper when requests fails.
        timeout: Request timeout in seconds.

    Returns:
        List of normalized event dicts.
    """
    parsed = urlparse(base_url or url)
    base_url = f"{parsed.scheme}://{parsed.netloc}/"

    session = create_scraper_session(verify_ssl=False, use_retries=True)

    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.warning(f"Standard fetch failed for {url}: {e}")
        if use_cloudscraper:
            from scripts.scraper_utils import create_cloudscraper_session
            cs = create_cloudscraper_session(base_url=url)
            if cs:
                try:
                    resp = cs.get(url, timeout=timeout)
                    resp.raise_for_status()
                    html = resp.text
                except Exception as e2:
                    logger.error(f"Cloudscraper fetch failed: {e2}")
                    return []
            else:
                return []
        else:
            return []

    try:
        events = extractor(html, base_url)
        return events
    except Exception as e:
        logger.error(f"Extractor failed for {url}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return []
