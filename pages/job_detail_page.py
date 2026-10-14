"""Page object for an individual job detail page."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from playwright.sync_api import expect

from pages.base_page import BasePage
from utils.datasets import DEFAULT_DATASET_ID

#: Form scenario exercised by this suite (``mock_site/src/data/scenarios.ts``).
DEFAULT_SCENARIO_ID = "simple-company-form"


class JobDetailPage(BasePage):
    TITLE = "article h1"
    EYEBROW = "[data-jd-eyebrow]"
    DESCRIPTION = "[data-jd-html]"
    JOB_SALARY = "[data-jd-salary]"
    JOB_EXPERIENCE = "[data-jd-experience]"
    JOB_ID_ATTRIBUTE = "data-jd-id"
    PAGER_LINK = "[data-job-pager-link]"
    SCENARIO_FORM = "[data-section='scenario-form']"
    NOT_FOUND = "[data-section='jd'][data-state='not-found']"
    JSONL_ERROR = "[data-jsonl-error]"
    SUBMIT_BUTTON = "button[data-action='submit-application']"

    def _detail_url(self, job_id, dataset_id, scenario_id) -> str:
        return f"/jd?scenarios={scenario_id}&id={job_id}&dataset={dataset_id}"

    def open(
        self,
        job_id: str | int,
        dataset_id: str = DEFAULT_DATASET_ID,
        scenario_id: str = DEFAULT_SCENARIO_ID,
    ) -> "JobDetailPage":
        """Open a job detail page and wait for its rendered title."""
        self.navigate(self._detail_url(job_id, dataset_id, scenario_id))
        self.wait_for_selector(self.TITLE)
        return self

    def open_by_id(
        self,
        job_id: str | int,
        dataset_id: str = DEFAULT_DATASET_ID,
        scenario_id: str = DEFAULT_SCENARIO_ID,
    ) -> "JobDetailPage":
        """Open a job detail page without waiting for a title.

        Use this for ids that may not exist, where the page renders a not-found state
        instead of ``TITLE`` and a title wait would time out.
        """
        self.navigate(self._detail_url(job_id, dataset_id, scenario_id))
        self.wait_for_selector(f"{self.NOT_FOUND}, {self.TITLE}", timeout=15000)
        return self

    def get_title(self) -> str:
        return self.inner_text(self.TITLE).strip()

    def get_dataset_and_level(self) -> str:
        return self.inner_text(self.EYEBROW).strip()

    def get_description(self) -> str:
        return self.inner_text(self.DESCRIPTION).strip()

    def get_salary(self) -> str:
        """Return the structured salary label, or an empty string when absent."""
        if not self.is_visible(self.JOB_SALARY, timeout=5000):
            return ""
        return self.inner_text(self.JOB_SALARY).strip()

    def get_experience(self) -> str:
        """Return the structured experience label, or an empty string when absent."""
        if not self.is_visible(self.JOB_EXPERIENCE, timeout=5000):
            return ""
        return self.inner_text(self.JOB_EXPERIENCE).strip()

    def get_rendered_job_id(self) -> str | None:
        """Return the ``data-jd-id`` the page actually rendered, not the one requested."""
        return self.page.locator(f"[data-section='jd']").first.get_attribute(self.JOB_ID_ATTRIBUTE)

    def is_job_not_found(self) -> bool:
        """Return whether the page is showing the "job id was not found" state."""
        return self.count(self.NOT_FOUND) == 1

    def not_found_message(self) -> str:
        return self.inner_text(f"{self.NOT_FOUND} {self.JSONL_ERROR}").strip()

    def jsonl_error_message(self) -> str:
        """Return the dataset-load error banner text, or an empty string when absent."""
        if not self.is_visible(self.JSONL_ERROR, timeout=10000):
            return ""
        return self.inner_text(self.JSONL_ERROR).strip()

    def open_application_section(self) -> "JobDetailPage":
        self.wait_for_selector(self.SCENARIO_FORM)
        self.page.locator(self.SCENARIO_FORM).scroll_into_view_if_needed()
        return self

    def _pager_target_id(self, text: str) -> str | None:
        """Return the job id a pager control points at, or ``None`` when disabled."""
        href = self.page.locator(self.PAGER_LINK).filter(has_text=text).first.get_attribute("href")
        if not href:
            return None
        return parse_qs(urlparse(href).query).get("id", [None])[0]

    def _wait_for_rendered_job_id(self, job_id: str | None, timeout: int = 10000) -> "JobDetailPage":
        """Wait until the page reports ``job_id`` as rendered.

        The title node survives the client-side re-render, so waiting on it alone can
        read the previous job's text. Waiting on ``data-jd-id`` cannot.
        """
        if job_id is not None:
            expect(self.page.locator(f"[data-section='jd']").first).to_have_attribute(
                self.JOB_ID_ATTRIBUTE, str(job_id), timeout=timeout
            )
        return self

    def previous_job(self) -> "JobDetailPage":
        target = self._pager_target_id("Previous")
        self.page.locator(self.PAGER_LINK).filter(has_text="Previous").first.click()
        return self._wait_for_rendered_job_id(target)

    def next_job(self) -> "JobDetailPage":
        target = self._pager_target_id("Next")
        self.page.locator(self.PAGER_LINK).filter(has_text="Next").first.click()
        return self._wait_for_rendered_job_id(target)

    def get_detail_url(self) -> str:
        return self.current_url()

    def is_application_form_visible(self) -> bool:
        return self.is_visible(self.SCENARIO_FORM, timeout=10000)

    def has_submit_control(self) -> bool:
        """Return whether an application submit button exists in the DOM at all.

        Distinct from :meth:`is_application_form_visible`, which answers whether the
        section is *shown*. BUG-002 is about a submit control existing where it must not.
        """
        return self.count(self.SUBMIT_BUTTON) > 0