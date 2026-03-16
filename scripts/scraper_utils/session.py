"""Reusable session setup for scrapers: headers, retries, optional cloudscraper."""

import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}


def create_scraper_session(
    verify_ssl: bool = True,
    use_retries: bool = True,
    retry_total: int = 3,
    retry_backoff: float = 1.0,
) -> requests.Session:
    """
    Create a requests Session with browser-like headers and retry logic.

    Args:
        verify_ssl: If False, disables SSL verification (for sites with cert issues).
        use_retries: If True, adds retry adapter for 5xx and connection errors.
        retry_total: Number of retries.
        retry_backoff: Backoff factor between retries.

    Returns:
        Configured requests.Session.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    session.verify = verify_ssl

    if not verify_ssl:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass

    if use_retries:
        retry_strategy = Retry(
            total=retry_total,
            backoff_factor=retry_backoff,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
            connect=retry_total,
            read=retry_total,
            redirect=retry_total,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

    return session


def create_cloudscraper_session(base_url: Optional[str] = None):
    """
    Create a cloudscraper session for sites that block standard requests.

    Returns None if cloudscraper is not installed.
    """
    if not CLOUDSCRAPER_AVAILABLE:
        logger.debug("cloudscraper not installed, cannot create cloudscraper session")
        return None

    try:
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'darwin', 'desktop': True}
        )
        scraper.headers.update(DEFAULT_HEADERS)
        scraper.verify = False
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass

        if base_url:
            try:
                scraper.get(base_url, timeout=15, verify=False)
            except Exception as e:
                logger.debug(f"Could not establish initial session: {e}")

        return scraper
    except Exception as e:
        logger.debug(f"Could not create cloudscraper session: {e}")
        return None
