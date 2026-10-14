"""Base page object shared by every page object in the framework.

Wraps common Playwright operations so individual pages stay focused on
selectors and business logic. All other pages inherit from :class:`BasePage`.
"""

from __future__ import annotations

import os
from typing import Any, Optional, Sequence

from playwright.sync_api import Page, Locator, Browser, BrowserContext


class BasePage:
    """Common Playwright helpers.

    Parameters
    ----------
    page:
        Playwright ``Page`` instance (usually injected by a pytest fixture).
    base_url:
        Root URL of the application under test, e.g. ``http://localhost:8000``.
        Relative paths passed to :meth:`navigate` are resolved against it.
    """

    def __init__(self, page: Page, base_url: str = ""):
        self.page = page
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #
    def navigate(self, path: str = "/", wait_until: str = "domcontentloaded") -> "BasePage":
        """Navigate to an absolute URL or a path relative to ``base_url``."""
        url = path if path.startswith(("http://", "https://", "file://")) else f"{self.base_url}{path if path.startswith('/') else '/' + path}"
        self.page.goto(url, wait_until=wait_until)
        return self

    def reload(self, wait_until: str = "domcontentloaded"):
        self.page.reload(wait_until=wait_until)
        return self

    def go_back(self):
        self.page.go_back()
        return self

    def go_forward(self):
        self.page.go_forward()
        return self

    def current_url(self) -> str:
        return self.page.url

    def title(self) -> str:
        return self.page.title()

    # ------------------------------------------------------------------ #
    # Element location helpers
    # ------------------------------------------------------------------ #
    def locator(self, selector: str) -> Locator:
        return self.page.locator(selector)

    def get_by_role(self, role: str, **kwargs: Any) -> Locator:
        return self.page.get_by_role(role, **kwargs)

    def get_by_text(self, text: str, **kwargs: Any) -> Locator:
        return self.page.get_by_text(text, **kwargs)

    def get_by_label(self, label: str, **kwargs: Any) -> Locator:
        return self.page.get_by_label(label, **kwargs)

    def get_by_placeholder(self, placeholder: str, **kwargs: Any) -> Locator:
        return self.page.get_by_placeholder(placeholder, **kwargs)

    def get_by_test_id(self, test_id: str) -> Locator:
        return self.page.get_by_test_id(test_id)

    # ------------------------------------------------------------------ #
    # Interactions
    # ------------------------------------------------------------------ #
    def click(self, selector: str, **kwargs: Any):
        self.page.locator(selector).click(**kwargs)
        return self

    def dbl_click(self, selector: str, **kwargs: Any):
        self.page.locator(selector).dblclick(**kwargs)
        return self

    def right_click(self, selector: str, **kwargs: Any):
        self.page.locator(selector).click(button="right", **kwargs)
        return self

    def hover(self, selector: str, **kwargs: Any):
        self.page.locator(selector).hover(**kwargs)
        return self

    def fill(self, selector: str, value: str, **kwargs: Any):
        """Clear an input and type ``value``."""
        locator = self.page.locator(selector)
        locator.fill(value, **kwargs)
        return self

    def type_text(self, selector: str, value: str, delay: int = 0, **kwargs: Any):
        self.page.locator(selector).type(value, delay=delay, **kwargs)
        return self

    def press(self, selector: str, key: str, **kwargs: Any):
        self.page.locator(selector).press(key, **kwargs)
        return self

    def clear(self, selector: str):
        self.page.locator(selector).fill("")
        return self

    def check(self, selector: str):
        self.page.locator(selector).check()
        return self

    def uncheck(self, selector: str):
        self.page.locator(selector).uncheck()
        return self

    def select_option(self, selector: str, value: Any, **kwargs: Any):
        self.page.locator(selector).select_option(value, **kwargs)
        return self

    def upload_file(self, selector: str, path: str):
        self.page.locator(selector).set_input_files(path)
        return self

    def focus(self, selector: str):
        self.page.locator(selector).focus()
        return self

    # ------------------------------------------------------------------ #
    # Waiting
    # ------------------------------------------------------------------ #
    def wait_for_selector(self, selector: str, state: str = "visible", timeout: Optional[int] = None):
        self.page.wait_for_selector(selector, state=state, timeout=timeout)
        return self

    def wait_for_url(self, url: str, timeout: Optional[int] = None):
        self.page.wait_for_url(url, timeout=timeout)
        return self

    def wait_for_load_state(self, state: str = "load"):
        self.page.wait_for_load_state(state)
        return self

    def wait_for_timeout(self, ms: int):
        self.page.wait_for_timeout(ms)
        return self

    # ------------------------------------------------------------------ #
    # Reading state
    # ------------------------------------------------------------------ #
    def text_content(self, selector: str) -> Optional[str]:
        return self.page.locator(selector).text_content()

    def inner_text(self, selector: str) -> str:
        return self.page.locator(selector).inner_text()

    def input_value(self, selector: str) -> str:
        return self.page.locator(selector).input_value()

    def get_attribute(self, selector: str, name: str) -> Optional[str]:
        return self.page.locator(selector).get_attribute(name)

    def count(self, selector: str) -> int:
        return self.page.locator(selector).count()

    def is_visible(self, selector: str, timeout: int = 0) -> bool:
        """Return whether ``selector`` is visible.

        A positive ``timeout`` waits up to that many milliseconds for the element
        to become visible; a zero timeout performs an immediate check.
        """
        try:
            if timeout and timeout > 0:
                self.page.wait_for_selector(selector, state="visible", timeout=timeout)
                return True
            return self.page.locator(selector).first.is_visible()
        except Exception:
            return False

    def is_enabled(self, selector: str) -> bool:
        return self.page.locator(selector).is_enabled()

    def is_checked(self, selector: str) -> bool:
        return self.page.locator(selector).is_checked()

    def all_texts(self, selector: str) -> list[str]:
        return self.page.locator(selector).all_inner_texts()

    # ------------------------------------------------------------------ #
    # Assertions-ish helpers
    # ------------------------------------------------------------------ #
    def has_text(self, selector: str, expected: str) -> bool:
        actual = (self.inner_text(selector) or "").strip()
        return expected in actual

    def body_text(self) -> str:
        """Return the rendered document text. Used by "did anything render at all" checks."""
        return self.page.locator("body").inner_text().strip()

    # ------------------------------------------------------------------ #
    # Misc
    # ------------------------------------------------------------------ #
    def screenshot(self, path: str, full_page: bool = False):
        self.page.screenshot(path=path, full_page=full_page)
        return self

    def set_viewport(self, width: int, height: int):
        self.page.set_viewport_size({"width": width, "height": height})
        return self

    def evaluate(self, expression: str, arg: Any = None):
        return self.page.evaluate(expression, arg)

    def close(self):
        self.page.close()
        return self

    # ------------------------------------------------------------------ #
    # Static browser helpers (optional manual launch)
    # ------------------------------------------------------------------ #
    @staticmethod
    def launch_browser(playwright, browser_name: str = "chromium", headless: bool = True, **kwargs: Any) -> Browser:
        """Launch a browser manually. Prefer pytest-playwright fixtures in tests."""
        if not hasattr(playwright, browser_name):
            raise ValueError(f"Unknown browser: {browser_name}")
        return getattr(playwright, browser_name).launch(headless=headless, **kwargs)

    @staticmethod
    def new_context(browser: Browser, **kwargs: Any) -> BrowserContext:
        return browser.new_context(**kwargs)

    @staticmethod
    def new_page(context: BrowserContext) -> Page:
        return context.new_page()