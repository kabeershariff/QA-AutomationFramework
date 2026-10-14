"""Page object for the job application form."""

from __future__ import annotations

import json
from typing import Any

from playwright.sync_api import expect

from pages.base_page import BasePage
from utils.datasets import DEFAULT_DATASET_ID

DEFAULT_SCENARIO_ID = "simple-company-form"

#: Extension list the resume input advertises via ``accept``
#: (``mock_site/src/scenarios/company-careers/simple-company-form/index.tsx:89``).
RESUME_ACCEPTED_EXTENSIONS = (".pdf", ".doc", ".docx")

_SUBMISSION_STORAGE_KEY = "applyground.latestSubmission"

#: Records every ``disabled`` transition of the submit button while installed.
_SUBMIT_GUARD_PROBE = """
(selector) => {
  const button = document.querySelector(selector);
  if (!button) return false;
  const states = [button.disabled];
  const observer = new MutationObserver(() => states.push(button.disabled));
  observer.observe(button, { attributes: true, attributeFilter: ['disabled'] });
  window.__submitGuard = { states, stop: () => observer.disconnect() };
  return true;
}
"""


class ApplicationFormPage(BasePage):
    NAME = "#field-fullName"
    EMAIL = "#field-email"
    PHONE = "#field-phone"
    LOCATION = "#field-location"
    RESUME = "#field-resume"
    PORTFOLIO = "#field-portfolioUrl"
    WORK_AUTH_YES = "#field-workAuthorization-yes"
    WORK_AUTH_NO = "#field-workAuthorization-no"
    CONFIRM = "#field-confirmAccurate"
    SUBMIT = "button[data-action='submit-application']"
    VALIDATION_SUMMARY = "[data-section='validation-summary']"
    MISSING_REQUIRED = "[data-list='missing-required'] [data-missing-field]"
    LOCAL_RESULT_BLOCK = "[data-inline-submission]"
    LOCAL_RESULT = "[data-inline-submission] > pre"
    FILE_LIST = "[data-file-list] li"
    FILE_META = "[data-file-list] [data-file-meta]"
    FIELD_ERROR = "[data-field-error]"
    RADIO_GROUP = "fieldset"

    NAME_LABEL = "Full name"
    EMAIL_LABEL = "Email"
    PHONE_LABEL = "Phone"
    LOCATION_LABEL = "Current location"
    RESUME_LABEL = "Resume"
    PORTFOLIO_LABEL = "Portfolio or profile URL"

    def open(
        self,
        job_id: str | int = "0",
        dataset_id: str = DEFAULT_DATASET_ID,
        scenario_id: str = DEFAULT_SCENARIO_ID,
    ) -> "ApplicationFormPage":
        self.navigate(f"/jd?scenarios={scenario_id}&id={job_id}&dataset={dataset_id}")
        self.wait_for_selector(self.SUBMIT)
        return self

    # ------------------------------------------------------------------ #
    # Field access
    #
    # Text inputs are located by their associated <label>, which both survives an id
    # rename and proves the label is correctly wired to its input.
    # ------------------------------------------------------------------ #
    def field(self, label: str):
        return self.page.get_by_label(label)

    def fill_name(self, value: str) -> "ApplicationFormPage":
        self.field(self.NAME_LABEL).fill(value)
        return self

    def fill_email(self, value: str) -> "ApplicationFormPage":
        self.field(self.EMAIL_LABEL).fill(value)
        return self

    def fill_phone(self, value: str) -> "ApplicationFormPage":
        self.field(self.PHONE_LABEL).fill(value)
        return self

    def fill_location(self, value: str) -> "ApplicationFormPage":
        self.field(self.LOCATION_LABEL).fill(value)
        return self

    def upload_resume(self, path: str) -> "ApplicationFormPage":
        self.page.locator(self.RESUME).set_input_files(path)
        return self

    def fill_portfolio(self, value: str) -> "ApplicationFormPage":
        self.field(self.PORTFOLIO_LABEL).fill(value)
        return self

    def set_work_authorization(self, value: str | bool) -> "ApplicationFormPage":
        if value is True or str(value).lower() in {"yes", "true", "1"}:
            self.check(self.WORK_AUTH_YES)
        else:
            self.check(self.WORK_AUTH_NO)
        return self

    def set_confirmation(self, checked: bool) -> "ApplicationFormPage":
        if checked:
            self.check(self.CONFIRM)
        else:
            self.uncheck(self.CONFIRM)
        return self

    def name_value(self) -> str:
        return self.field(self.NAME_LABEL).input_value()

    def email_value(self) -> str:
        return self.field(self.EMAIL_LABEL).input_value()

    def location_value(self) -> str:
        return self.field(self.LOCATION_LABEL).input_value()

    def portfolio_value(self) -> str:
        return self.field(self.PORTFOLIO_LABEL).input_value()

    def aria_invalid(self, label: str) -> str:
        """Return an input's ``aria-invalid`` value (``"true"``/``"false"``/``None``)."""
        return self.field(label).get_attribute("aria-invalid")

    def has_labelled_field(self, label: str) -> bool:
        """Return whether exactly one input is reachable by its associated label."""
        return self.field(label).count() == 1

    def max_name_length(self) -> int | None:
        """Return the declared ``maxlength`` of the name input, or ``None`` when unset.

        ``-1`` is the DOM default for an input with no ``maxlength`` attribute.
        """
        declared = self.field(self.NAME_LABEL).get_attribute("maxlength")
        return -1 if declared is None else int(declared)

    def fill_valid_application(self, resume_path: str, name: str = "Jane Doe") -> "ApplicationFormPage":
        """Fill every required field with a valid value, ready for submission."""
        self.fill_name(name)
        self.fill_email("jane.doe@example.com")
        self.fill_location("Remote")
        self.upload_resume(resume_path)
        self.set_work_authorization("yes")
        return self

    # ------------------------------------------------------------------ #
    # Submission
    # ------------------------------------------------------------------ #
    def submit(self) -> "ApplicationFormPage":
        self.click(self.SUBMIT)
        return self

    def submit_rapidly(self, clicks: int = 2) -> "ApplicationFormPage":
        """Fire ``clicks`` submit activations back-to-back without awaiting between them.

        Uses ``HTMLElement.click()`` inside the page rather than Playwright's click,
        which would wait for actionability and let React settle between clicks. This
        reproduces a panicking or double-tapping candidate.
        """
        handle = self.page.locator(self.SUBMIT).element_handle()
        try:
            for _ in range(clicks):
                handle.evaluate("element => element.click()")
        finally:
            handle.dispose()
        return self

    def is_submit_disabled(self) -> bool:
        return not self.is_enabled(self.SUBMIT)

    def begin_submit_guard(self) -> bool:
        """Start recording every ``disabled`` transition of the submit button.

        Returns ``False`` when the button is absent, so a caller can fail with a
        meaningful message instead of comparing against an empty list.
        """
        return bool(self.page.evaluate(_SUBMIT_GUARD_PROBE, self.SUBMIT))

    def submit_guard_states(self) -> list[bool]:
        """Return the recorded disabled-states and stop recording."""
        states = self.page.evaluate(
            """() => {
                const guard = window.__submitGuard;
                if (!guard) return [];
                guard.stop();
                delete window.__submitGuard;
                return guard.states;
            }"""
        )
        return list(states)

    # ------------------------------------------------------------------ #
    # Validation output
    # ------------------------------------------------------------------ #
    def validation_summary(self) -> str:
        if not self.is_visible(self.VALIDATION_SUMMARY, timeout=10000):
            return ""
        return self.inner_text(self.VALIDATION_SUMMARY).strip()

    def missing_required_fields(self) -> list[str]:
        return self.all_texts(self.MISSING_REQUIRED)

    def field_error_messages(self) -> list[str]:
        """Return the text of every rendered per-field error."""
        return self.all_texts(self.FIELD_ERROR)

    def work_authorization_legend(self) -> str:
        """Return the radio group's ``<legend>`` text.

        A radio group must be labelled by a legend rather than a bare label; this is the
        only way to assert that from the accessibility tree.
        """
        return self.inner_text(f"{self.RADIO_GROUP}[data-field='workAuthorization'] legend").strip()

    # ------------------------------------------------------------------ #
    # Inline submission result
    # ------------------------------------------------------------------ #
    def result_block_count(self) -> int:
        """Return the number of inline submission blocks rendered."""
        return self.count(self.LOCAL_RESULT)

    def wait_for_result(self, timeout: int = 10000) -> "ApplicationFormPage":
        """Auto-retry until the inline submission result is attached to the DOM.

        Replaces a fixed sleep with an observable-state wait, so the suite is neither
        flaky on a slow runner nor dead time on a fast one. Waits for *attachment*
        rather than visibility because the result lives inside a collapsed ``<details>``.
        """
        expect(self.page.locator(self.LOCAL_RESULT_BLOCK)).to_be_attached(timeout=timeout)
        return self

    def local_result_json(self) -> dict[str, Any]:
        """Return the inline submission JSON block, expanded or not."""
        text = (self.page.locator(self.LOCAL_RESULT).first.text_content() or "").strip()
        return json.loads(text)

    def validation_warnings(self) -> list[str]:
        """Return the non-blocking warnings the app actually reported.

        Reads ``validation.warnings`` from the submission result rather than returning
        a hardcoded empty list, so an assertion written against this method can fail.
        """
        if self.result_block_count() == 0:
            return []
        return list(self.local_result_json().get("validation", {}).get("warnings", []))

    def stored_submission(self) -> dict[str, Any] | None:
        """Return the submission persisted to ``sessionStorage``, if any."""
        raw = self.page.evaluate("key => window.sessionStorage.getItem(key)", _SUBMISSION_STORAGE_KEY)
        return None if raw is None else json.loads(raw)

    def stored_submission_count(self) -> int:
        """Return how many submissions the app persisted.

        The app keeps a single latest-submission slot, so this is ``0`` or ``1``. It is
        the observable form of "no duplicate submission was created".
        """
        return sum(
            1
            for key in self.page.evaluate("() => Object.keys(window.sessionStorage)")
            if key == _SUBMISSION_STORAGE_KEY and self.page.evaluate("k => window.sessionStorage.getItem(k)", key)
        )

    def clear_stored_submissions(self) -> "ApplicationFormPage":
        self.page.evaluate("key => window.sessionStorage.removeItem(key)", _SUBMISSION_STORAGE_KEY)
        return self

    # ------------------------------------------------------------------ #
    # Resume metadata
    # ------------------------------------------------------------------ #
    def resume_metadata(self) -> str:
        return self.page.locator(self.RESUME).input_value()

    def resume_file_names(self) -> list[str]:
        """Return the file names listed under the resume input."""
        return [
            text.split(" (")[0].strip()
            for text in self.all_texts(self.FILE_LIST)
        ]

    def resume_metadata_text(self) -> list[str]:
        """Return the ``(type, N bytes)`` metadata strings listed for the resume."""
        return self.all_texts(self.FILE_META)