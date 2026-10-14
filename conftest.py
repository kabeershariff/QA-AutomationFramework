"""Shared pytest fixtures.

Provides application base URLs, browser context configuration, dataset access, and
failure-artifact handling for the automation suites.

Every suite in this repository runs against the local portal copy in ``mock_site``.
No test submits to the deployed instance; see ``reports/bugs/BUG-001.md`` for the
manually filed defect that can only be observed on the deployed build.
"""

from __future__ import annotations

import http.server
import json
import os
import socket
import socketserver
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from data.resume_files import PDF_BYTES, RESUME_NAME
from utils.datasets import DEFAULT_DATASET_ID, load_dataset

MOCK_URL = "http://127.0.0.1:8765"

_MOCK_DIST = Path(__file__).resolve().parent / "mock_site" / "dist"
_MOCK_HTTPD: http.server.ThreadingHTTPServer | None = None

#: A dataset label that only this application's ``manifest.json`` advertises. Used to
#: prove the thing answering on the port is *our* build, not merely something alive.
IDENTITY_DATASET_LABEL = "qa_fake_jobs"


def _url_reachable(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status < 500
    except Exception:
        return False


def _assert_target_identity(url: str) -> None:
    """Fail loudly unless ``url`` is serving this repository's application build.

    Reachability is not identity: any process already bound to the port would answer
    ``_url_reachable`` and turn the whole suite green against an unknown application.
    """
    manifest_url = f"{url}/data/manifest.json"
    try:
        with urllib.request.urlopen(manifest_url, timeout=5) as response:
            manifest = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as error:
        pytest.fail(
            f"Refusing to run against {url}: could not read {manifest_url} ({error}). "
            "Free the port or set MOCK_BASE_URL to a server built from mock_site/."
        )

    labels = {entry.get("label") for entry in manifest} if isinstance(manifest, list) else set()
    if IDENTITY_DATASET_LABEL not in labels:
        pytest.fail(
            f"Refusing to run against {url}: it serves a different application. "
            f"{manifest_url} advertises {sorted(labels)}, which does not include "
            f"{IDENTITY_DATASET_LABEL!r}. Something else is bound to that port."
        )


def _start_mock_server(port: int) -> http.server.ThreadingHTTPServer:
    class Handler(http.server.SimpleHTTPRequestHandler):
        """Static file handler that falls back to index.html for client-side routes."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(_MOCK_DIST), **kwargs)

        def send_head(self):
            target = self.translate_path(self.path)
            if not os.path.exists(target) and not os.path.splitext(target)[1]:
                self.path = "/index.html"
            return super().send_head()

    socketserver.TCPServer.allow_reuse_address = True
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


@pytest.fixture(scope="session")
def app_url(mock_app_url):
    """Default target: the local copy of the portal kept in this repository."""
    return os.getenv("BASE_URL", mock_app_url).rstrip("/")


@pytest.fixture(scope="session")
def mock_app_url():
    """Base URL for the local mock application, with an identity check."""
    url = os.getenv("MOCK_BASE_URL", MOCK_URL).rstrip("/")
    global _MOCK_HTTPD
    if not _url_reachable(url):
        parsed = url.replace("http://", "").replace("https://", "")
        host = parsed.split(":")[0]
        port = int(parsed.split(":")[1]) if ":" in parsed else 80
        if host in {"127.0.0.1", "localhost"} and _MOCK_DIST.is_dir():
            _MOCK_HTTPD = _start_mock_server(port)
            deadline = time.time() + 10
            while time.time() < deadline and not _url_reachable(url):
                time.sleep(0.25)
    _assert_target_identity(url)
    yield url
    if _MOCK_HTTPD is not None:
        _MOCK_HTTPD.shutdown()
        _MOCK_HTTPD = None


@pytest.fixture(scope="session")
def jobs_dataset():
    """Every record of the default 1000-row dataset, in file order."""
    return load_dataset(DEFAULT_DATASET_ID)


@pytest.fixture(scope="session")
def jobs_by_id(jobs_dataset):
    """The default dataset keyed by ``str(job["id"])``."""
    return {str(job["id"]): job for job in jobs_dataset}


@pytest.fixture
def resume_file(tmp_path):
    """A small synthetic resume. Metadata-only — the application never stores the bytes.

    Written with a ``.pdf`` extension so the fixture stays valid once BUG-004 is fixed
    and the ``accept`` list starts being enforced.
    """
    path = tmp_path / RESUME_NAME
    path.write_bytes(PDF_BYTES)
    return str(path)


@pytest.fixture
def browser_context_args(browser_context_args):
    """Shared browser context settings for all tests."""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "locale": "en-US",
        "timezone_id": "America/New_York",
    }