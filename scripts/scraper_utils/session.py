"""Reusable session setup for scrapers: headers, retries, optional cloudscraper."""

import logging
import os
import platform as plat_module
import ssl
from typing import Dict, Optional

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


def _cloudscraper_platform() -> str:
    """Detect platform for cloudscraper (Railway/Linux vs darwin vs windows)."""
    detected = plat_module.system().lower()
    if detected == 'linux' or os.environ.get('RAILWAY_ENVIRONMENT'):
        return 'linux'
    if detected == 'darwin':
        return 'darwin'
    return 'windows'


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, '').strip().lower() in ('1', 'true', 'yes', 'on')


def _use_proxy_explicitly_off(env_use_proxy: str) -> bool:
    """USE_PROXY_<KEY> set to a disabling value."""
    v = env_use_proxy.strip().lower()
    return v in ('0', 'false', 'no', 'off')


def _deploy_like_runtime() -> bool:
    """Railway/deploy, or local simulation of deploy proxy defaults."""
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        return True
    if os.environ.get('RAILWAY_PROJECT_ID'):
        return True
    if _env_truthy('PLANNER_SIMULATE_DEPLOY_PROXY'):
        return True
    return False


def scraper_proxy_opt_in(scraper_key: str) -> bool:
    """
    Return True when this scraper should use a Webshare proxy (``WEBSHARE_PROXY_*`` must be set).

    **Deployed (Railway / cron / hosted admin):** proxy is **on by default** for every scraper
    that calls this helper, when Webshare URLs are configured.

    **Local development:** proxy is **off by default** unless ``USE_PROXY_<KEY>=1`` or
    ``SCRAPER_PROXY_LOCAL_ENABLED=1``.

    **Escape hatches:**

    - ``SCRAPER_PROXY_GLOBAL_DISABLED=1`` or ``WEBSHARE_PROXY_DISABLED=1`` — disable proxy for all.
    - ``DISABLE_PROXY_<KEY>=1`` — disable for one scraper (e.g. ``DISABLE_PROXY_NGA``).
    - ``USE_PROXY_<KEY>=0`` — per-scraper off.

    Keys use upper snake_case (``nga``, ``asian_art``, ``finding_awe``, ``saam``).
    """
    if get_webshare_proxy_dict() is None:
        return False

    if _env_truthy('SCRAPER_PROXY_GLOBAL_DISABLED') or _env_truthy('WEBSHARE_PROXY_DISABLED'):
        return False

    norm = scraper_key.strip().lower().replace('-', '_')
    upper = norm.upper()

    if _env_truthy(f'DISABLE_PROXY_{upper}'):
        return False

    use_key = f'USE_PROXY_{upper}'
    use_val = os.environ.get(use_key, '')
    if _use_proxy_explicitly_off(use_val):
        return False

    if _env_truthy(use_key):
        return True

    if _deploy_like_runtime():
        return True

    if _env_truthy('SCRAPER_PROXY_LOCAL_ENABLED'):
        return True

    return False


def get_webshare_proxy_dict() -> Optional[Dict[str, str]]:
    """
    Build a requests-compatible proxies dict from environment variables.

    Resolution order:
    - WEBSHARE_PROXY_URL: if set, used for both http and https (typical Webshare single endpoint).
    - Else WEBSHARE_PROXY_HTTP / WEBSHARE_PROXY_HTTPS: per-scheme URLs; if only one is set,
      it is reused for both schemes (common for residential proxies).

    Returns None if no proxy env vars are set (caller should not use a proxy).
    """
    combined = os.environ.get('WEBSHARE_PROXY_URL', '').strip()
    if combined:
        return {'http': combined, 'https': combined}

    http_p = os.environ.get('WEBSHARE_PROXY_HTTP', '').strip()
    https_p = os.environ.get('WEBSHARE_PROXY_HTTPS', '').strip()
    if not http_p and not https_p:
        return None

    if http_p and https_p:
        return {'http': http_p, 'https': https_p}
    single = http_p or https_p
    return {'http': single, 'https': single}


def apply_webshare_proxy_to_session(session: requests.Session, use_proxy: bool = False) -> bool:
    """
    Optionally attach Webshare proxy settings to a requests-compatible session.

    Args:
        session: requests.Session or cloudscraper session (subclass).
        use_proxy: When True, apply proxies from env if configured (opt-in per scraper).

    Returns:
        True if proxies were applied, False otherwise.
    """
    if not use_proxy:
        return False
    proxies = get_webshare_proxy_dict()
    if not proxies:
        logger.debug('use_proxy=True but no WEBSHARE_PROXY_* env vars set; session unchanged')
        return False
    session.proxies.update(proxies)
    logger.debug('Applied Webshare proxy from environment to session')
    return True


class _SSLAdapter(HTTPAdapter):
    """Adapter that disables SSL verification for sites with cert issues."""

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)


def create_scraper_session(
    verify_ssl: bool = True,
    use_retries: bool = True,
    retry_total: int = 3,
    retry_backoff: float = 1.0,
    use_proxy: bool = False,
) -> requests.Session:
    """
    Create a requests Session with browser-like headers and retry logic.

    Args:
        verify_ssl: If False, disables SSL verification (for sites with cert issues).
        use_retries: If True, adds retry adapter for 5xx and connection errors.
        retry_total: Number of retries.
        retry_backoff: Backoff factor between retries.
        use_proxy: If True, attach Webshare proxy from WEBSHARE_PROXY_* env when set.

    Returns:
        Configured requests.Session.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    session.verify = verify_ssl

    apply_webshare_proxy_to_session(session, use_proxy=use_proxy)

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


def create_cloudscraper_session(
    base_url: Optional[str] = None,
    verify_ssl: bool = False,
    use_proxy: bool = False,
):
    """
    Create a cloudscraper session for sites that block standard requests.

    Uses platform detection (darwin/linux/windows, Railway), default headers,
    and optional base_url warmup.

    Args:
        base_url: If set, visit this URL first to establish session/cookies.
        verify_ssl: If True, use default SSL verification (no custom adapter).
            If False (default), disable SSL verification and use custom adapter
            for sites with cert issues (Hirshhorn, tulipday, etc.).
        use_proxy: If True, attach Webshare proxy from WEBSHARE_PROXY_* env when set.

    Returns None if cloudscraper is not installed.
    """
    if not CLOUDSCRAPER_AVAILABLE:
        logger.debug("cloudscraper not installed, cannot create cloudscraper session")
        return None

    try:
        platform_name = _cloudscraper_platform()
        scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': platform_name, 'desktop': True}
        )
        scraper.headers.update(DEFAULT_HEADERS)
        scraper.verify = verify_ssl

        apply_webshare_proxy_to_session(scraper, use_proxy=use_proxy)

        if not verify_ssl:
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass
            scraper.mount('https://', _SSLAdapter())

        if base_url:
            try:
                scraper.get(base_url, timeout=15, verify=verify_ssl)
            except Exception as e:
                logger.debug(f"Could not establish initial session: {e}")

        return scraper
    except Exception as e:
        logger.debug(f"Could not create cloudscraper session: {e}")
        return None
