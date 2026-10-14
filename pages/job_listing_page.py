"""Page object for the job listings page."""

from __future__ import annotations

from playwright.sync_api import expect

from pages.base_page import BasePage


class JobListingsPage(BasePage):
    PATH = "/"

    JOB_ROW = "[data-job-row]"
    JOB_ID_ATTRIBUTE = "data-job-id"
    JOB_TITLE = "[data-job-title]"
    JOB_META = "[data-job-meta]"
    JOB_LEVEL = "[data-job-meta] span:first-child"
    JOB_EXCERPT = "[data-job-excerpt]"
    JOB_LINK = "[data-job-row-link]"
    JOB_SALARY = "[data-job-salary]"
    JOB_EXPERIENCE = "[data-job-experience]"
    LEVEL_FILTER = "[data-job-filters] label:first-of-type select"
    DATASET_FILTER = "[data-job-filters] label:nth-of-type(2) select"
    INDEX_STATUS = "[data-job-index-status]"
    JSONL_ERROR = "[data-jsonl-error]"
    PAGINATION = "[data-section='pagination']"

    def open(self, dataset: str | None = None) -> "JobListingsPage":
        path = self.PATH if dataset is None else f"{self.PATH}?dataset={dataset}"
        self.navigate(path)
        self.wait_for_selector(self.JOB_ROW)
        return self

    # ------------------------------------------------------------------ #
    # Cards
    # ------------------------------------------------------------------ #
    def get_job_cards(self):
        return self.page.locator(self.JOB_ROW)

    def get_job_count(self) -> int:
        """Return the number of rendered rows. Does **not** auto-wait for a re-render.

        Prefer ``expect(page.get_job_cards()).to_have_count(n)`` after a filter change,
        because filter selection triggers an async re-render this count can race.
        """
        return self.count(self.JOB_ROW)

    def job_ids(self) -> list[str]:
        ids: list[str] = []
        for index in range(self.get_job_count()):
            value = self.get_job_cards().nth(index).get_attribute(self.JOB_ID_ATTRIBUTE)
            if value is not None:
                ids.append(value)
        return ids

    def job_titles(self) -> list[str]:
        return self.all_texts(self.JOB_TITLE)

    def job_levels(self) -> list[str]:
        return self.all_texts(self.JOB_LEVEL)

    def job_excerpts(self) -> list[str]:
        return self.all_texts(self.JOB_EXCERPT)

    def job_salaries(self) -> list[str]:
        """Return the salary label text of every card exposing structured salary data."""
        return self.all_texts(self.JOB_SALARY)

    def job_experiences(self) -> list[str]:
        """Return the experience label text of every card exposing structured experience data."""
        return self.all_texts(self.JOB_EXPERIENCE)

    def open_job(self, index: int = 0) -> None:
        self.page.locator(self.JOB_LINK).nth(index).click()

    # ------------------------------------------------------------------ #
    # Filters
    # ------------------------------------------------------------------ #
    def filter_by_level(self, level: str) -> "JobListingsPage":
        """Select a job level in the level filter (``"all"`` clears it)."""
        self.page.get_by_label("Level").select_option(level)
        return self

    def filter_by_dataset(self, dataset: str) -> "JobListingsPage":
        self.page.get_by_label("Dataset").select_option(dataset)
        return self

    def get_selected_level(self) -> str:
        return self.page.get_by_label("Level").input_value()

    def current_dataset(self) -> str:
        return self.page.get_by_label("Dataset").input_value()

    def index_status(self) -> str:
        """Return the ``1-50 of 1000`` index summary rendered above the listing."""
        return self.inner_text(self.INDEX_STATUS).strip()

    # ------------------------------------------------------------------ #
    # Pagination
    # ------------------------------------------------------------------ #
    def pagination_status(self) -> str:
        """Return the ``Page 1 / 20`` label."""
        return self.inner_text(f"{self.PAGINATION} span").strip()

    def total_pages(self) -> int:
        """Parse the page count out of :meth:`pagination_status`."""
        _, _, total = self.pagination_status().rpartition("/")
        return int(total.strip().split()[0])

    def current_page(self) -> int:
        head, _, _ = self.pagination_status().partition("/")
        return int(head.split()[-1])

    def go_to_next_page(self) -> "JobListingsPage":
        self.page.get_by_role("button", name="Next").click()
        return self

    def go_to_previous_page(self) -> "JobListingsPage":
        self.page.get_by_role("button", name="Previous").click()
        return self

    def is_next_enabled(self) -> bool:
        return self.page.get_by_role("button", name="Next").is_enabled()

    def is_previous_enabled(self) -> bool:
        return self.page.get_by_role("button", name="Previous").is_enabled()

    # ------------------------------------------------------------------ #
    # Error state
    # ------------------------------------------------------------------ #
    def wait_for_error(self, timeout: int = 15000) -> "JobListingsPage":
        """Auto-retry until the dataset-load error banner is attached."""
        expect(self.page.locator(self.JSONL_ERROR)).to_be_attached(timeout=timeout)
        return self

    def jsonl_error_message(self) -> str:
        """Return the dataset-load error banner text, or an empty string when absent."""
        if not self.is_visible(self.JSONL_ERROR, timeout=10000):
            return ""
        return self.inner_text(self.JSONL_ERROR).strip()