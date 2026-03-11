import os
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
        self._in_h3 = False
        self._current_h3 = ""
        self.h3_texts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        attrs_map = dict(attrs)
        element_id = attrs_map.get("id")
        if element_id:
            self.element_ids.add(element_id)

        if tag == "a":
            href = attrs_map.get("href")
            if element_id and href:
                self.href_by_id[element_id] = href

        if tag == "h3":
            self._in_h3 = True
            self._current_h3 = ""

    def handle_data(self, data: str) -> None:  # type: ignore[override]
        if self._in_h3:
            self._current_h3 += data

    def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
        if tag == "h3":
            self._in_h3 = False
            self.h3_texts.append(self._current_h3.strip())


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

    if not any(title for title in parser.h3_texts):
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
    try:
        html = _fetch_html(url)
    except HTTPError as exc:
        if exc.code == 429:
            return "inconclusive", f"#{index} {name} -> {url} | HTTP error 429 (rate limited)"
        return "invalid", f"#{index} {name} -> {url} | HTTP error {exc.code}"
    except URLError as exc:
        return "invalid", f"#{index} {name} -> {url} | URL error: {exc.reason}"
    except TimeoutError:
        return "invalid", f"#{index} {name} -> {url} | timeout"
    except Exception as exc:  # pragma: no cover
        return "invalid", f"#{index} {name} -> {url} | unexpected error: {exc}"

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

    max_workers = int(os.getenv("WHATSAPP_LINK_TEST_WORKERS", "8"))
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
