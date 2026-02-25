"""
Data gathering service using web scraping.
Discovers Singapore malls from singmalls.app, enriches region data from Wikipedia,
and saves store directories to the database — no AI API calls required.
"""
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Mall, Store, MallStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SINGMALLS_BASE = "https://singmalls.app"
WIKI_MALLS_URL = "https://en.wikipedia.org/wiki/List_of_shopping_malls_in_Singapore"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 15
INTER_REQUEST_DELAY = 1.0
MAX_RETRIES = 3

CAPITALAND_BASE = "https://www.capitaland.com"
CAPITALAND_MALLS_URL = f"{CAPITALAND_BASE}/sg/en/shop/malls.html"
CAPITALAND_PLAYWRIGHT_TIMEOUT = 30000  # ms

CAPITALAND_CATEGORY_MAP = {
    "fnb": "Food & Beverage",
    "beautyandwellness": "Beauty & Wellness",
    "fashion": "Fashion",
    "lifestyle": "Lifestyle",
    "entertainment": "Entertainment",
    "services": "Services",
    "homeandliving": "Home & Living",
    "sportsandleisure": "Sports & Leisure",
    "jewelryandaccessories": "Jewelry & Accessories",
    "kidsandbabies": "Kids & Babies",
    "educationandlearning": "Education & Learning",
}

REGION_HEADING_MAP = {
    "Central Region": "Central",
    "North Region": "North",
    "North-East Region": "North-East",
    "East Region": "East",
    "West Region": "West",
    "South": "South",
    "Central": "Central",
    "North": "North",
    "East": "East",
    "West": "West",
}

# Singapore postal code prefix → region
POSTAL_PREFIX_TO_REGION = {
    "01": "Central", "02": "Central", "03": "Central", "04": "Central",
    "05": "Central", "06": "Central", "07": "Central", "08": "Central",
    "09": "Central", "10": "Central", "11": "Central", "12": "Central",
    "13": "Central", "14": "Central", "15": "Central", "16": "East",
    "17": "Central", "18": "East", "19": "East", "20": "Central",
    "21": "Central", "22": "Central", "23": "Central", "24": "West",
    "25": "West", "26": "West", "27": "West", "28": "North",
    "29": "North", "30": "North", "31": "North", "32": "North",
    "33": "North", "34": "North", "35": "North", "36": "North",
    "37": "North", "38": "North", "39": "North", "40": "North",
    "41": "North", "42": "East", "43": "East", "44": "East",
    "45": "East", "46": "East", "47": "East", "48": "East",
    "49": "West", "50": "Central", "51": "Central", "52": "Central",
    "53": "North-East", "54": "North-East", "55": "North-East",
    "56": "North-East", "57": "North-East", "58": "West", "59": "West",
    "60": "West", "61": "West", "62": "West", "63": "West", "64": "West",
    "65": "West", "66": "West", "67": "West", "68": "West", "69": "West",
    "70": "South", "71": "South", "72": "East", "73": "East",
    "75": "East", "76": "East", "77": "East", "78": "East",
    "79": "North-East", "80": "North-East", "81": "East",
    "82": "North-East", "83": "Central", "84": "Central",
}

# ---------------------------------------------------------------------------
# Global job state (single-process; replace with Redis for multi-worker)
# ---------------------------------------------------------------------------
_job_state: dict = {
    "job_id": None,
    "status": "idle",
    "total_malls": 0,
    "completed_malls": 0,
    "current_mall": None,
    "error": None,
}


def get_job_state() -> dict:
    return dict(_job_state)


def _update_state(**kwargs):
    _job_state.update(kwargs)


def _normalize(name: str) -> str:
    """Lowercase, strip punctuation for deduplication."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _http_get(url: str, session: requests.Session) -> Optional[requests.Response]:
    """GET with retry logic and 429 back-off. Returns Response or None."""
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Rate-limited on {url}, waiting {wait}s")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            else:
                logger.warning(f"Failed to fetch {url} after {MAX_RETRIES} attempts: {e}")
    return None


# ---------------------------------------------------------------------------
# SingMalls scrapers
# ---------------------------------------------------------------------------

def _extract_next_data(html: str) -> Optional[dict]:
    """Parse the __NEXT_DATA__ JSON blob embedded in Next.js SSR HTML."""
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag or not tag.string:
        return None
    try:
        return json.loads(tag.string)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse __NEXT_DATA__: {e}")
        return None


def _scrape_singmalls_mall_list(session: requests.Session) -> list:
    """
    Fetch singmalls.app/en/malls and return a list of
    {"name": ..., "slug": ..., "address": ...} dicts.
    """
    url = f"{SINGMALLS_BASE}/en/malls"
    resp = _http_get(url, session)
    if not resp:
        return []

    data = _extract_next_data(resp.text)
    if not data:
        logger.warning("No __NEXT_DATA__ found on singmalls.app/en/malls")
        return []

    try:
        malls_raw = data["props"]["pageProps"]["sites"]
    except (KeyError, TypeError):
        logger.warning("Unexpected __NEXT_DATA__ structure for mall list")
        return []

    result = []
    for m in malls_raw:
        name = (m.get("name") or "").strip()
        slug = (m.get("id") or m.get("slug") or "").strip()
        address = (m.get("formattedAddress") or m.get("address") or "").strip()
        if name and slug:
            result.append({"name": name, "slug": slug, "address": address})

    logger.info(f"SingMalls: found {len(result)} malls")
    return result


def _scrape_singmalls_stores(slug: str, session: requests.Session) -> list:
    """
    Fetch singmalls.app/en/malls/{slug}/directory and return a list of
    {"name": ..., "category": ..., "unit": ...} dicts.
    """
    url = f"{SINGMALLS_BASE}/en/malls/{slug}/directory"
    resp = _http_get(url, session)
    if not resp:
        return []

    data = _extract_next_data(resp.text)
    if not data:
        return []

    try:
        merchants = data["props"]["pageProps"]["merchants"]
    except (KeyError, TypeError):
        return []

    result = []
    for m in merchants:
        name = (m.get("name") or "").strip()
        if not name:
            continue
        category = (m.get("formattedCategories") or m.get("category") or "").strip() or None
        unit = (m.get("formattedLots") or m.get("unit") or "").strip() or None
        result.append({"name": name, "category": category, "unit": unit})

    return result


# ---------------------------------------------------------------------------
# Wikipedia region map
# ---------------------------------------------------------------------------

def _scrape_wiki_region_map(session: requests.Session) -> dict:
    """
    Parse the Wikipedia 'List of shopping malls in Singapore' page.
    Each region is an <h2 id="Region"> followed by a <div class="div-col"> with <li> items.
    Returns {normalized_mall_name: region_string}.
    """
    resp = _http_get(WIKI_MALLS_URL, session)
    if not resp:
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")
    region_map: dict = {}

    for region_id, region_label in [
        ("Central", "Central"),
        ("East", "East"),
        ("North", "North"),
        ("North-East", "North-East"),
        ("West", "West"),
    ]:
        h2 = soup.find("h2", id=region_id)
        if not h2:
            continue
        # find_next searches forward from h2's parent to the next div.div-col
        div_col = h2.parent.find_next("div", class_="div-col")
        if not div_col:
            continue
        for li in div_col.find_all("li"):
            mall_name = li.get_text(strip=True)
            if mall_name:
                region_map[_normalize(mall_name)] = region_label

    logger.info(f"Wikipedia: mapped {len(region_map)} malls to regions")
    return region_map


# ---------------------------------------------------------------------------
# CapitaLand scrapers
# ---------------------------------------------------------------------------

def _scrape_capitaland_mall_list(session: requests.Session) -> list:
    """
    Fetch CapitaLand malls index (SSR) and return
    [{"name": str, "slug": str, "address": str}] dicts.
    Links in the page are shaped like /sg/malls/{slug}/en.html.
    """
    resp = _http_get(CAPITALAND_MALLS_URL, session)
    if not resp:
        logger.warning("CapitaLand: failed to fetch malls index")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    result = []
    seen_slugs: set = set()
    slug_re = re.compile(r"/sg/malls/([^/]+)/en\.html")

    for a in soup.find_all("a", href=True):
        m = slug_re.search(a["href"])
        if not m:
            continue
        slug = m.group(1)
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        # Prefer link text; fall back to nearest heading; finally humanise slug
        name = a.get_text(strip=True)
        if not name:
            for parent in a.parents:
                h = parent.find(["h2", "h3", "h4"])
                if h:
                    name = h.get_text(strip=True)
                    break
        if not name:
            name = slug.replace("-", " ").title()

        result.append({"name": name, "slug": slug, "address": ""})

    logger.info(f"CapitaLand: found {len(result)} malls")
    return result


def _parse_capitaland_api_stores(data: dict) -> list:
    """
    Parse the CapitaLand paginated tenant API response.
    Expected format: {"totalcount": N, "properties": [...]}
    Each item: {"jcr:title": str, "unitnumber": [...], "marketingcategory": [...]}
    """
    items = data.get("properties", [])
    if not isinstance(items, list):
        return []

    result = []
    for item in items:
        if not isinstance(item, dict):
            continue

        # Name
        name = (item.get("jcr:title") or "").strip()
        if not name:
            details = item.get("_rel_brandtenants_details", [])
            if details and isinstance(details, list) and isinstance(details[0], dict):
                name = (details[0].get("jcr:title") or "").strip()
        if not name:
            continue

        # Unit: tag-path like "…/unit-03-k1" → "#03-K1"
        unit = None
        unit_list = item.get("unitnumber", [])
        if unit_list and isinstance(unit_list, list):
            segment = unit_list[0].split("/")[-1]
            segment = re.sub(r"^unit-", "", segment, flags=re.IGNORECASE)
            unit = "#" + segment.upper()

        # Category: tag-path, second-to-last segment → human label
        category = None
        cat_list = item.get("marketingcategory", [])
        if cat_list and isinstance(cat_list, list):
            parts = cat_list[0].split("/")
            raw_key = parts[-2] if len(parts) >= 2 else parts[0]
            cat_key = raw_key.lower().replace("-", "").replace(" ", "")
            category = CAPITALAND_CATEGORY_MAP.get(cat_key) or raw_key.replace("-", " ").title()

        result.append({"name": name, "category": category, "unit": unit})

    return result


def _scrape_capitaland_stores(mall_slug: str) -> list:
    """
    Use Playwright (headless Chromium) to load a CapitaLand store-directory
    page, intercept the paginated tenant API response (api-v1/.../tenants/...),
    and paginate through all results using browser fetch (preserving cookies).
    Returns [{"name": str, "category": str|None, "unit": str|None}].
    """
    url = f"{CAPITALAND_BASE}/sg/malls/{mall_slug}/en/stores.html"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("playwright not installed — skipping CapitaLand store scraping. "
                       "Run: .venv/bin/pip install playwright && "
                       ".venv/bin/python -m playwright install chromium")
        return []

    first_api_url: Optional[str] = None
    first_data: Optional[dict] = None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=REQUEST_HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            def handle_response(response):
                nonlocal first_api_url, first_data
                if first_data is not None:
                    return  # already captured the first paginated response
                ct = response.headers.get("content-type", "")
                if "json" not in ct:
                    return
                resp_url = response.url
                if "api-v1" not in resp_url or "tenants" not in resp_url:
                    return
                try:
                    data = response.json()
                    if isinstance(data, dict) and "totalcount" in data:
                        first_api_url = resp_url
                        first_data = data
                except Exception:
                    pass

            page.on("response", handle_response)

            try:
                page.goto(url, timeout=CAPITALAND_PLAYWRIGHT_TIMEOUT,
                          wait_until="domcontentloaded")
            except Exception as e:
                logger.warning(f"CapitaLand: page load issue for {mall_slug}: {e}")

            # Fixed wait replaces networkidle — avoids New Relic beacon timeouts
            page.wait_for_timeout(8000)

            if first_data is None:
                logger.warning(f"CapitaLand: no API response captured for {mall_slug}")
                browser.close()
                return []

            all_stores = _parse_capitaland_api_stores(first_data)
            total_count = first_data.get("totalcount", 0)
            logger.info(
                f"CapitaLand {mall_slug}: totalcount={total_count}, "
                f"first page={len(all_stores)} stores"
            )

            # Paginate remaining pages via browser fetch (preserves session cookies)
            if total_count > 100:
                base_url = re.sub(r"/cl%3Apgcursor/\d+/\d+\.json$", "", first_api_url)
                if base_url != first_api_url:
                    for start in range(101, total_count + 1, 100):
                        page_url = f"{base_url}/cl%3Apgcursor/{start}/100.json"
                        try:
                            result = page.evaluate(
                                f'fetch("{page_url}", {{credentials:"include"}}).then(r=>r.json())'
                            )
                            page_stores = _parse_capitaland_api_stores(result)
                            all_stores.extend(page_stores)
                            logger.info(
                                f"  → Page starting at {start}: {len(page_stores)} stores"
                            )
                        except Exception as e:
                            logger.warning(f"  → Pagination failed at start={start}: {e}")
                            break

            browser.close()
    except Exception as e:
        logger.warning(f"CapitaLand: Playwright error for {mall_slug}: {e}")
        return []

    return all_stores


# ---------------------------------------------------------------------------
# Region helpers
# ---------------------------------------------------------------------------

def _infer_region_from_address(address: str) -> Optional[str]:
    """Extract Singapore postal code from address and map prefix to region."""
    if not address:
        return None
    match = re.search(r"(?:Singapore\s+)?(\d{6})", address)
    if not match:
        return None
    prefix = match.group(1)[:2]
    return POSTAL_PREFIX_TO_REGION.get(prefix)


def _build_mall_data(raw: dict, wiki_map: dict) -> dict:
    """
    Map a raw SingMalls entry to the dict expected by _upsert_mall.
    Region priority: Wikipedia lookup → postal code inference.
    """
    name = raw.get("name", "").strip()
    address = raw.get("address", "").strip()
    slug = raw.get("slug", "")
    website = f"{SINGMALLS_BASE}/en/malls/{slug}" if slug else None

    region = wiki_map.get(_normalize(name)) or _infer_region_from_address(address)

    return {
        "name": name,
        "address": address or None,
        "region": region,
        "website": website,
    }


def _parse_floor_from_unit(unit: Optional[str]) -> Optional[str]:
    """Extract floor number from a unit string like '#03-24A' → '3'."""
    if not unit:
        return None
    match = re.match(r"#?(\d+)-", unit)
    if match:
        return str(int(match.group(1)))  # strip leading zeros
    return None


# ---------------------------------------------------------------------------
# DB helpers (unchanged)
# ---------------------------------------------------------------------------

def _upsert_mall(db: Session, mall_data: dict) -> Optional[Mall]:
    name = mall_data.get("name", "").strip()
    if not name:
        return None
    mall = db.query(Mall).filter(Mall.name == name).first()
    if not mall:
        mall = Mall(
            name=name,
            address=mall_data.get("address"),
            region=mall_data.get("region"),
            website=mall_data.get("website"),
            last_updated=datetime.now(timezone.utc),
        )
        db.add(mall)
        db.commit()
        db.refresh(mall)
    else:
        mall.address = mall_data.get("address") or mall.address
        mall.region = mall_data.get("region") or mall.region
        mall.website = mall_data.get("website") or mall.website
        mall.last_updated = datetime.now(timezone.utc)
        db.commit()
        db.refresh(mall)
    return mall


def _upsert_store(db: Session, store_name: str, category: Optional[str]) -> Store:
    norm = _normalize(store_name)
    store = db.query(Store).filter(Store.normalized_name == norm).first()
    if not store:
        store = Store(name=store_name, category=category, normalized_name=norm)
        db.add(store)
        db.commit()
        db.refresh(store)
    return store


def _upsert_mall_store(db: Session, mall: Mall, store: Store, floor: Optional[str], unit: Optional[str]):
    existing = (
        db.query(MallStore)
        .filter(MallStore.mall_id == mall.id, MallStore.store_id == store.id)
        .first()
    )
    if not existing:
        ms = MallStore(mall_id=mall.id, store_id=store.id, floor=floor, unit_number=unit)
        db.add(ms)
        db.commit()


# ---------------------------------------------------------------------------
# Main job
# ---------------------------------------------------------------------------

def run_gather_job(job_id: str):
    """
    Main background job.
    Phase 1: fetch mall + region lists.
    Phase 2: scrape SingMalls store directories.
    Phase 3: scrape CapitaLand store directories via Playwright.
    """
    _update_state(job_id=job_id, status="running", total_malls=0, completed_malls=0,
                  current_mall=None, error=None)

    db = SessionLocal()
    http = requests.Session()

    try:
        # Phase 1: Fetch mall lists and region map
        logger.info("Phase 1: Scraping mall list from singmalls.app...")
        _update_state(current_mall="Fetching mall list...")
        raw_malls = _scrape_singmalls_mall_list(http)

        if not raw_malls:
            _update_state(status="error", error="Failed to scrape mall list from singmalls.app")
            return

        logger.info("Phase 1: Fetching region map from Wikipedia...")
        _update_state(current_mall="Fetching region data...")
        wiki_map = _scrape_wiki_region_map(http)

        logger.info("Phase 1: Fetching CapitaLand mall list...")
        _update_state(current_mall="Fetching CapitaLand mall list...")
        capitaland_malls = _scrape_capitaland_mall_list(http)

        total = len(raw_malls) + len(capitaland_malls)
        _update_state(total_malls=total)
        logger.info(
            f"Phase 1 complete: {len(raw_malls)} SingMalls + "
            f"{len(capitaland_malls)} CapitaLand = {total} total malls"
        )

        # Phase 2: SingMalls store directories
        for i, raw in enumerate(raw_malls):
            mall_name = raw.get("name", "").strip()
            if not mall_name:
                continue

            _update_state(current_mall=mall_name, completed_malls=i)
            logger.info(f"[{i+1}/{len(raw_malls)}] SingMalls: {mall_name}")

            mall_data = _build_mall_data(raw, wiki_map)
            mall = _upsert_mall(db, mall_data)
            if not mall:
                continue

            try:
                stores = _scrape_singmalls_stores(raw["slug"], http)
                for s in stores:
                    store_name = s.get("name", "").strip()
                    if not store_name:
                        continue
                    unit = s.get("unit")
                    floor = _parse_floor_from_unit(unit)
                    store = _upsert_store(db, store_name, s.get("category"))
                    _upsert_mall_store(db, mall, store, floor, unit)

                logger.info(f"  → Saved {len(stores)} stores for {mall_name}")
            except Exception as e:
                logger.warning(f"  → Failed to scrape stores for {mall_name}: {e}")

            time.sleep(INTER_REQUEST_DELAY)

        singmalls_done = len(raw_malls)

        # Phase 3: CapitaLand store directories (Playwright)
        if capitaland_malls:
            logger.info(
                f"Phase 3: Scraping store directories for "
                f"{len(capitaland_malls)} CapitaLand malls via Playwright..."
            )
            for j, mall_info in enumerate(capitaland_malls):
                mall_name = mall_info["name"]
                _update_state(
                    current_mall=f"[CapitaLand] {mall_name}",
                    completed_malls=singmalls_done + j,
                )
                logger.info(
                    f"[CapitaLand {j+1}/{len(capitaland_malls)}] Processing: {mall_name}"
                )

                address = mall_info.get("address") or ""
                mall_data = {
                    "name": mall_name,
                    "address": address or None,
                    "region": (
                        wiki_map.get(_normalize(mall_name))
                        or _infer_region_from_address(address)
                    ),
                    "website": (
                        f"{CAPITALAND_BASE}/sg/malls/{mall_info['slug']}/en.html"
                    ),
                }
                mall = _upsert_mall(db, mall_data)
                if not mall:
                    continue

                try:
                    stores = _scrape_capitaland_stores(mall_info["slug"])
                    for s in stores:
                        store_name = s.get("name", "").strip()
                        if not store_name:
                            continue
                        unit = s.get("unit")
                        floor = _parse_floor_from_unit(unit)
                        store = _upsert_store(db, store_name, s.get("category"))
                        _upsert_mall_store(db, mall, store, floor, unit)

                    logger.info(f"  → Saved {len(stores)} stores for {mall_name}")
                except Exception as e:
                    logger.warning(
                        f"  → Failed to scrape CapitaLand stores for {mall_name}: {e}"
                    )

                time.sleep(INTER_REQUEST_DELAY)

        _update_state(status="done", completed_malls=total, current_mall=None)
        logger.info("Data gathering complete.")

    except Exception as e:
        logger.exception("Data gathering job failed")
        _update_state(status="error", error=str(e))
    finally:
        db.close()
        http.close()
