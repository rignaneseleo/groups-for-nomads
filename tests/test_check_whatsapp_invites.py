import json
import os
import sys
from urllib.error import HTTPError, URLError

import pytest
import yaml

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
)

import check_whatsapp_invites as checker


OFFLINE_URL = "https://chat.whatsapp.com/OFFLINEcode1"
RATE_LIMITED_URL = "https://chat.whatsapp.com/RATELIMITcode1"
UNREACHABLE_URL = "https://chat.whatsapp.com/URLERRORcode1"

VALID_HTML = """
<html><body>
  <div id="main_block">
    <img src="https://example.com/group.jpg">
    <h3>Live Group Name</h3>
    <a id="action-button" href="https://chat.whatsapp.com/OKcode1">Join</a>
    <a id="whatsapp-web-button" href="https://web.whatsapp.com/accept?code=OKcode1">Web</a>
  </div>
</body></html>
"""


def _http_error(code: int) -> HTTPError:
    return HTTPError(
        url="https://chat.whatsapp.com/x", code=code, msg="err", hdrs=None, fp=None
    )


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Make every wait instant so the tests run fast."""
    monkeypatch.setattr(checker.time, "sleep", lambda _seconds: None)


def _write_data_file(tmp_path, groups):
    data_path = tmp_path / "data.yaml"
    data_path.write_text(
        yaml.safe_dump({"version": "1.0", "groups": groups}, sort_keys=False),
        encoding="utf-8",
    )
    return data_path


def _run(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["check_whatsapp_invites.py"] + argv)
    return checker.main()


def test_persistent_429_is_inconclusive_not_offline(monkeypatch, capsys):
    def fake_fetch(url, timeout_seconds=15):
        raise _http_error(429)

    monkeypatch.setattr(checker, "_fetch_html", fake_fetch)

    result = checker._validate_link(
        RATE_LIMITED_URL, retries=1, rate_limit_wait_s=900, rate_limit_max_waits=3
    )

    assert result.status == "inconclusive"
    assert result.reason == "HTTP 429 (rate limited)"
    out = capsys.readouterr().out
    assert "RATE LIMITED: waiting 900s (wait 1/3)" in out
    assert "RATE LIMITED: waiting 900s (wait 3/3)" in out


def test_429_then_success_is_active(monkeypatch):
    calls = {"n": 0}

    def fake_fetch(url, timeout_seconds=15):
        calls["n"] += 1
        if calls["n"] <= 3:
            raise _http_error(429)
        return VALID_HTML

    monkeypatch.setattr(checker, "_fetch_html", fake_fetch)

    result = checker._validate_link(
        RATE_LIMITED_URL, retries=1, rate_limit_wait_s=5, rate_limit_max_waits=5
    )

    assert result.status == "active"
    assert result.title == "Live Group Name"


def test_http_404_is_inactive(monkeypatch):
    def fake_fetch(url, timeout_seconds=15):
        raise _http_error(404)

    monkeypatch.setattr(checker, "_fetch_html", fake_fetch)

    result = checker._validate_link(OFFLINE_URL, retries=1)

    assert result.status == "inactive"
    assert result.reason == "HTTP 404"


def test_url_error_is_inconclusive(monkeypatch):
    def fake_fetch(url, timeout_seconds=15):
        raise URLError("connection reset")

    monkeypatch.setattr(checker, "_fetch_html", fake_fetch)

    result = checker._validate_link(UNREACHABLE_URL, retries=1)

    assert result.status == "inconclusive"
    assert "connection reset" in result.reason


def test_http_500_is_inconclusive(monkeypatch):
    def fake_fetch(url, timeout_seconds=15):
        raise _http_error(503)

    monkeypatch.setattr(checker, "_fetch_html", fake_fetch)

    result = checker._validate_link(UNREACHABLE_URL, retries=1)

    assert result.status == "inconclusive"
    assert result.reason == "HTTP 503 (server error)"


def test_apply_keeps_rate_limited_group(monkeypatch, tmp_path, capsys):
    groups = [
        {"name": "Rate Limited Group", "platform": "whatsapp", "url": RATE_LIMITED_URL},
        {"name": "Offline Group", "platform": "whatsapp", "url": OFFLINE_URL},
    ]
    data_path = _write_data_file(tmp_path, groups)

    def fake_fetch(url, timeout_seconds=15):
        if url == RATE_LIMITED_URL:
            raise _http_error(429)
        raise _http_error(404)

    monkeypatch.setattr(checker, "_fetch_html", fake_fetch)

    exit_code = _run(
        monkeypatch,
        [
            "--data-file",
            str(data_path),
            "--delay-ms",
            "0",
            "--jitter-ms",
            "0",
            "--retries",
            "0",
            "--rate-limit-wait-s",
            "1",
            "--rate-limit-max-waits",
            "2",
            "--apply",
        ],
    )

    out = capsys.readouterr().out
    assert exit_code == 1  # the 404 group is genuinely offline
    assert "INCONCLUSIVE Rate Limited Group" in out
    assert "OFFLINE Offline Group" in out
    assert "Offline groups: 1" in out
    assert "Inconclusive groups: 1" in out

    remaining = yaml.safe_load(data_path.read_text(encoding="utf-8"))["groups"]
    remaining_urls = [g["url"] for g in remaining]
    assert RATE_LIMITED_URL in remaining_urls
    assert OFFLINE_URL not in remaining_urls


def test_inconclusive_alone_does_not_fail(monkeypatch, tmp_path):
    groups = [
        {"name": "Rate Limited Group", "platform": "whatsapp", "url": RATE_LIMITED_URL}
    ]
    data_path = _write_data_file(tmp_path, groups)

    monkeypatch.setattr(
        checker, "_fetch_html", lambda url, timeout_seconds=15: (_ for _ in ()).throw(_http_error(429))
    )

    exit_code = _run(
        monkeypatch,
        [
            "--data-file",
            str(data_path),
            "--delay-ms",
            "0",
            "--jitter-ms",
            "0",
            "--retries",
            "0",
            "--rate-limit-max-waits",
            "1",
        ],
    )

    assert exit_code == 0


def test_report_file_content(monkeypatch, tmp_path):
    mismatch_url = "https://chat.whatsapp.com/OKcode1"
    groups = [
        {"name": "Stale Name", "platform": "whatsapp", "url": mismatch_url},
        {"name": "Offline Group", "platform": "whatsapp", "url": OFFLINE_URL},
        {"name": "Rate Limited Group", "platform": "whatsapp", "url": RATE_LIMITED_URL},
    ]
    data_path = _write_data_file(tmp_path, groups)
    report_path = tmp_path / "report.json"

    def fake_fetch(url, timeout_seconds=15):
        if url == mismatch_url:
            return VALID_HTML
        if url == OFFLINE_URL:
            raise _http_error(404)
        raise _http_error(429)

    monkeypatch.setattr(checker, "_fetch_html", fake_fetch)

    exit_code = _run(
        monkeypatch,
        [
            "--data-file",
            str(data_path),
            "--delay-ms",
            "0",
            "--jitter-ms",
            "0",
            "--retries",
            "0",
            "--rate-limit-max-waits",
            "1",
            "--report-file",
            str(report_path),
        ],
    )

    assert exit_code == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["checked"] == 3
    assert report["offline"] == [
        {"name": "Offline Group", "url": OFFLINE_URL, "reason": "HTTP 404"}
    ]
    assert report["inconclusive"] == [
        {
            "name": "Rate Limited Group",
            "url": RATE_LIMITED_URL,
            "reason": "HTTP 429 (rate limited)",
        }
    ]
    assert report["mismatches"] == [
        {
            "current_name": "Stale Name",
            "live_name": "Live Group Name",
            "url": mismatch_url,
        }
    ]
