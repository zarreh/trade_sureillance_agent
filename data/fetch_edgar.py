"""Downloads SEC EDGAR Insider Transactions bulk data sets into data/raw/.

See docs/PLAN.md §4.1. Fetches the target quarter plus the two preceding
quarters so every transaction in the target quarter has a full 180-day history
behind it — two quarters alone does not guarantee that for transactions early
in the target window.

Sends a descriptive User-Agent with a contact email and paces requests, per
SEC's fair-access policy (https://www.sec.gov/os/webmaster-faq#developers).

Deliberately does NOT hardcode a deep link to the current quarter's zip: the
URL prefix has changed at least once between quarters (observed
`.../structureddata/...` for older quarters vs. `.../datastandardsinnovation/...`
for the newest), so the download URL is discovered from the live listing page.
"""

from __future__ import annotations

import io
import re
import time
import zipfile
from pathlib import Path

import httpx
import truststore

# Use the OS certificate trust store rather than certifi's bundled list, so this
# works unmodified behind a corporate TLS-inspecting proxy (common in enterprise
# networks) as well as on the open internet.
truststore.inject_into_ssl()

LISTING_URL = "https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
ZIP_HREF_PATTERN = re.compile(r'href="([^"]*/(\d{4})q(\d)_form345\.zip)"')
REQUEST_PACING_SECONDS = 0.3


class EdgarFetchError(RuntimeError):
    pass


def user_agent(contact_email: str) -> str:
    """SEC requires a descriptive User-Agent identifying the requester and a contact."""
    return f"TradeSurveillanceAgent research prototype ({contact_email})"


def discover_quarter_urls(client: httpx.Client, listing_url: str = LISTING_URL) -> dict[str, str]:
    """Scrapes the listing page for every available quarter's zip URL.

    Scraping the live page rather than constructing a URL from a fixed pattern
    is deliberate — see the module docstring.
    """
    response = client.get(listing_url)
    response.raise_for_status()
    urls: dict[str, str] = {}
    for href, year, quarter in ZIP_HREF_PATTERN.findall(response.text):
        label = f"{year}q{quarter}"
        urls[label] = href if href.startswith("http") else f"https://www.sec.gov{href}"
    if not urls:
        raise EdgarFetchError(f"No quarterly zip links found on {listing_url}")
    return urls


def previous_quarters(quarter: str, count: int) -> list[str]:
    """Returns the `count` quarters strictly before `quarter`, oldest first."""
    year, qtr = int(quarter[:4]), int(quarter[5])
    result = []
    for _ in range(count):
        qtr -= 1
        if qtr == 0:
            qtr = 4
            year -= 1
        result.append(f"{year}q{qtr}")
    return list(reversed(result))


def latest_quarter(available: dict[str, str]) -> str:
    return max(available, key=lambda q: (int(q[:4]), int(q[5])))


def download_and_extract(url: str, dest_dir: Path, client: httpx.Client) -> None:
    response = client.get(url, follow_redirects=True)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        zf.extractall(dest_dir)


def fetch_quarters(quarters: list[str], raw_dir: Path, contact_email: str) -> None:
    """Downloads each quarter into its own subdirectory (`raw_dir/<quarter>/`).

    Every quarter's zip contains identically-named TSVs (SUBMISSION.tsv, etc.),
    so extracting them all into one flat directory would silently overwrite
    every earlier quarter with the last one downloaded. build_store.py reads
    every subdirectory and concatenates them.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": user_agent(contact_email)}
    with httpx.Client(headers=headers, timeout=60.0) as client:
        available = discover_quarter_urls(client)
        missing = [q for q in quarters if q not in available]
        if missing:
            raise EdgarFetchError(f"Quarter(s) not found on listing page: {missing}")
        for quarter in quarters:
            quarter_dir = raw_dir / quarter
            print(f"Fetching {quarter} from {available[quarter]}")
            download_and_extract(available[quarter], quarter_dir, client)
            time.sleep(REQUEST_PACING_SECONDS)


def main() -> None:
    from surveillance.settings import get_settings

    settings = get_settings()
    contact_email = "research@zarreh.ai"
    with httpx.Client(headers={"User-Agent": user_agent(contact_email)}, timeout=60.0) as client:
        available = discover_quarter_urls(client)
    target = latest_quarter(available)
    quarters = [*previous_quarters(target, 2), target]
    print(f"Target quarter: {target}. Fetching: {quarters}")
    fetch_quarters(quarters, Path(settings.data_dir) / "raw", contact_email)


if __name__ == "__main__":
    main()
