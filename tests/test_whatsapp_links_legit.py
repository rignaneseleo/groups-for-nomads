import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest
import yaml


@dataclass
class InvitePageCheck:
    is_legit: bool
    reason: str


class WhatsAppInviteHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.element_ids: set[str] = set()
        self.href_by_id: dict[str, str] = {}
        self._tag_depth = 0
        self._main_block_depth: Optional[int] = None
        self._in_main_block_h3 = False
        self._current_h3 = ""
        self.main_block_h3_texts: list[str] = []
        self.main_block_has_image = False

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        self._tag_depth += 1
        attrs_map = dict(attrs)
        element_id = attrs_map.get("id")
        if element_id:
            self.element_ids.add(element_id)
            if element_id == "main_block":
                self._main_block_depth = self._tag_depth

        if tag == "a":
            href = attrs_map.get("href")
            if element_id and href:
                self.href_by_id[element_id] = href

        in_main_block = (
            self._main_block_depth is not None and self._tag_depth > self._main_block_depth
        )

        if tag == "img" and in_main_block and attrs_map.get("src"):
            self.main_block_has_image = True

        if tag == "h3" and in_main_block:
            self._in_main_block_h3 = True
            self._current_h3 = ""

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._in_main_block_h3:
            self._current_h3 += data

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag == "h3" and self._in_main_block_h3:
            self._in_main_block_h3 = False
            self.main_block_h3_texts.append(self._current_h3.strip())

        if self._main_block_depth is not None and self._tag_depth == self._main_block_depth:
            self._main_block_depth = None

        if self._tag_depth > 0:
            self._tag_depth -= 1


def check_whatsapp_invite_html(html: str) -> InvitePageCheck:
    parser = WhatsAppInviteHTMLParser()
    parser.feed(html)

    if "main_block" not in parser.element_ids:
        return InvitePageCheck(False, "missing #main_block")

    action_button_href = parser.href_by_id.get("action-button", "")
    if not action_button_href.startswith("https://chat.whatsapp.com/"):
        return InvitePageCheck(False, "missing/invalid #action-button invite href")

    web_button_href = parser.href_by_id.get("whatsapp-web-button", "")
    if not web_button_href.startswith("https://web.whatsapp.com/accept?code="):
        return InvitePageCheck(False, "missing/invalid #whatsapp-web-button href")

    if not parser.main_block_has_image:
        return InvitePageCheck(False, "group image is missing")

    if not any(title for title in parser.main_block_h3_texts):
        return InvitePageCheck(False, "group title is empty")

    return InvitePageCheck(True, "ok")


def _fetch_html(url: str, timeout_seconds: int = 12) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read(250_000).decode("utf-8", errors="replace")


def _read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(parsed, 0)


def _sleep_with_jitter(base_delay_ms: int, jitter_ms: int) -> None:
    if base_delay_ms <= 0 and jitter_ms <= 0:
        return
    extra = random.randint(0, jitter_ms) if jitter_ms > 0 else 0
    time.sleep((base_delay_ms + extra) / 1000.0)


def _extract_whatsapp_groups():
    data_path = Path(__file__).resolve().parents[1] / "data.yaml"
    with data_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    groups = []
    for index, group in enumerate(data.get("groups", []), start=1):
        entry = group or {}
        url = entry.get("url")
        if not isinstance(url, str):
            continue
        normalized = url.strip()
        if normalized.startswith("https://chat.whatsapp.com/"):
            groups.append((index, entry.get("name", "<unknown>"), normalized))
    return groups


def _validate_group_link(index: int, name: str, url: str) -> tuple[str, Optional[str]]:
    delay_ms = _read_int_env("WHATSAPP_LINK_DELAY_MS", 0)
    jitter_ms = _read_int_env("WHATSAPP_LINK_JITTER_MS", 0)
    max_retries = _read_int_env("WHATSAPP_LINK_MAX_RETRIES", 2)
    retry_backoff_ms = _read_int_env("WHATSAPP_LINK_RETRY_BACKOFF_MS", 1500)

    for attempt in range(max_retries + 1):
        _sleep_with_jitter(delay_ms, jitter_ms)
        try:
            html = _fetch_html(url)
            break
        except HTTPError as exc:
            if exc.code == 429:
                if attempt < max_retries:
                    time.sleep((retry_backoff_ms * (2**attempt)) / 1000.0)
                    continue
                return (
                    "inconclusive",
                    f"#{index} {name} -> {url} | HTTP error 429 (rate limited)",
                )
            return "invalid", f"#{index} {name} -> {url} | HTTP error {exc.code}"
        except URLError as exc:
            return "invalid", f"#{index} {name} -> {url} | URL error: {exc.reason}"
        except TimeoutError:
            return "invalid", f"#{index} {name} -> {url} | timeout"
        except Exception as exc:  # pragma: no cover
            return "invalid", f"#{index} {name} -> {url} | unexpected error: {exc}"
    else:
        return "inconclusive", f"#{index} {name} -> {url} | exhausted retries"

    result = check_whatsapp_invite_html(html)
    if not result.is_legit:
        return "invalid", f"#{index} {name} -> {url} | invalid invite page: {result.reason}"
    return "ok", None


def test_check_whatsapp_invite_html_legit_sample():
    legit_html = """
    <div id="main_block">
      <a href="https://chat.whatsapp.com/CKz9WY1IWjSIh9htQ72RR3" id="action-button">
        <span>Apri l'app</span>
      </a>
      <img src="https://mmg.whatsapp.net/d/f/AwExample.jpg" alt="Group icon" />
      <h3 class="_9vd5 _9scr">South America Travelling</h3>
      <h4>Invito alla chat di gruppo</h4>
      <a href="https://web.whatsapp.com/accept?code=CKz9WY1IWjSIh9htQ72RR3&utm_campaign=wa_chat_v2" id="whatsapp-web-button">
        <span>Continua su WhatsApp Web</span>
      </a>
    </div>
    """
    result = check_whatsapp_invite_html(legit_html)
    assert result.is_legit, result.reason


def test_check_whatsapp_invite_html_probably_not_legit_sample():
    suspicious_html = """
    <div id="main_block">
      <a href="https://chat.whatsapp.com/CxC8pFQJ86F1L6xyfyccGQ" id="action-button">
        <span>Apri l'app</span>
      </a>
      <img src="https://mmg.whatsapp.net/d/f/AwExample.jpg" alt="Group icon" />
      <h3 class="_9vd5 _9scr"></h3>
      <h4>Invito alla chat di gruppo</h4>
      <a href="https://web.whatsapp.com/accept?code=CxC8pFQJ86F1L6xyfyccGQ&utm_campaign=wa_chat_v2" id="whatsapp-web-button">
        <span>Continua su WhatsApp Web</span>
      </a>
    </div>
    """
    result = check_whatsapp_invite_html(suspicious_html)
    assert not result.is_legit
    assert result.reason == "group title is empty"


@pytest.mark.skipif(
    os.getenv("RUN_WHATSAPP_LINK_TESTS") != "1",
    reason="Set RUN_WHATSAPP_LINK_TESTS=1 to run live WhatsApp link checks.",
)
def test_data_yaml_whatsapp_links_open_legit_invite_pages():
    whatsapp_groups = _extract_whatsapp_groups()
    assert whatsapp_groups, "No WhatsApp invite links found in data.yaml"

    default_workers = "1" if os.getenv("GITHUB_ACTIONS") == "true" else "8"
    max_workers = max(1, int(os.getenv("WHATSAPP_LINK_TEST_WORKERS", default_workers)))
    total = len(whatsapp_groups)
    invalid_failures: list[str] = []
    inconclusive_failures: list[str] = []
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_validate_group_link, index, name, url)
            for index, name, url in whatsapp_groups
        ]
        for future in as_completed(futures):
            status, message = future.result()
            completed += 1
            if not message:
                print(
                    f"[{completed}/{total}] ok",
                    flush=True,
                )
                continue
            if status == "inconclusive":
                inconclusive_failures.append(message)
                print(f"[{completed}/{total}] inconclusive - {message}", flush=True)
            else:
                invalid_failures.append(message)
                print(f"[{completed}/{total}] invalid - {message}", flush=True)

    assert not invalid_failures, "Invalid WhatsApp invite links:\n" + "\n".join(
        sorted(invalid_failures)
    )
    if inconclusive_failures:
        pytest.skip(
            "WhatsApp rate-limited automated checks. Inconclusive links:\n"
            + "\n".join(sorted(inconclusive_failures))
        )
