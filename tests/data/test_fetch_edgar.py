# ruff: noqa: E501 - fixture URLs are one contiguous string; wrapping would break adjacency
import zipfile
from io import BytesIO
from pathlib import Path

import httpx
import respx

from data.fetch_edgar import (
    LISTING_URL,
    discover_quarter_urls,
    download_and_extract,
    fetch_quarters,
    latest_quarter,
    previous_quarters,
    user_agent,
)

FAKE_LISTING_HTML = """
<table>
<tr><td><a href="/files/datastandardsinnovation/data/insider-transactions-data-sets/2026q2_form345.zip">2026 Q2</a></td></tr>
<tr><td><a href="/files/structureddata/data/insider-transactions-data-sets/2026q1_form345.zip">2026 Q1</a></td></tr>
<tr><td><a href="/files/structureddata/data/insider-transactions-data-sets/2025q4_form345.zip">2025 Q4</a></td></tr>
</table>
"""


def test_user_agent_includes_contact_email() -> None:
    assert "research@zarreh.ai" in user_agent("research@zarreh.ai")


def test_previous_quarters_handles_year_rollover() -> None:
    assert previous_quarters("2026q1", 2) == ["2025q3", "2025q4"]


def test_previous_quarters_simple_case() -> None:
    assert previous_quarters("2026q2", 2) == ["2025q4", "2026q1"]


@respx.mock
def test_discover_quarter_urls_handles_changed_path_prefix() -> None:
    respx.get(LISTING_URL).mock(return_value=httpx.Response(200, text=FAKE_LISTING_HTML))
    with httpx.Client() as client:
        urls = discover_quarter_urls(client)
    # The newest quarter uses a different path prefix than older ones — both must resolve.
    assert urls["2026q2"].endswith(
        "/datastandardsinnovation/data/insider-transactions-data-sets/2026q2_form345.zip"
    )
    assert urls["2025q4"].endswith(
        "/structureddata/data/insider-transactions-data-sets/2025q4_form345.zip"
    )


def test_latest_quarter_picks_max_by_year_then_quarter() -> None:
    available = {"2025q4": "x", "2026q1": "y", "2026q2": "z"}
    assert latest_quarter(available) == "2026q2"


@respx.mock
def test_download_and_extract_writes_files(tmp_path: Path) -> None:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("SUBMISSION.tsv", "ACCESSION_NUMBER\tFILING_DATE\n")
    respx.get("https://example.com/fake.zip").mock(
        return_value=httpx.Response(200, content=buffer.getvalue())
    )
    with httpx.Client() as client:
        download_and_extract("https://example.com/fake.zip", tmp_path, client)
    assert (tmp_path / "SUBMISSION.tsv").exists()


@respx.mock
def test_fetch_quarters_extracts_each_quarter_into_its_own_subdirectory(tmp_path: Path) -> None:
    """Every quarter's zip has identically-named TSVs — a shared flat directory
    would silently overwrite each earlier quarter with the last one downloaded."""
    respx.get(LISTING_URL).mock(return_value=httpx.Response(200, text=FAKE_LISTING_HTML))
    for quarter in ("2025q4", "2026q1", "2026q2"):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("SUBMISSION.tsv", f"quarter={quarter}\n")
        respx.get(url__regex=rf".*{quarter}_form345\.zip").mock(
            return_value=httpx.Response(200, content=buffer.getvalue())
        )

    fetch_quarters(["2025q4", "2026q1", "2026q2"], tmp_path, "research@zarreh.ai")

    for quarter in ("2025q4", "2026q1", "2026q2"):
        content = (tmp_path / quarter / "SUBMISSION.tsv").read_text()
        assert content == f"quarter={quarter}\n"


@respx.mock
def test_fetch_quarters_raises_on_missing_quarter(tmp_path: Path) -> None:
    respx.get(LISTING_URL).mock(return_value=httpx.Response(200, text=FAKE_LISTING_HTML))
    try:
        fetch_quarters(["1999q1"], tmp_path, "research@zarreh.ai")
    except Exception as exc:  # noqa: BLE001 - asserting the specific message below
        assert "1999q1" in str(exc)
    else:
        raise AssertionError("expected EdgarFetchError")
