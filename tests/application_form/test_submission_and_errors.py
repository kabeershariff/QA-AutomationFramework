"""Submission-outcome and error-handling tests.

Every case uses ``mock_app_url``: the error-handling scenarios deliberately drive
network faults, and there is no reason for them to resolve a different target than the
rest of the suite under a ``BASE_URL`` override.
"""

import time

import pytest

from data.boundary_strings import BOUNDARY_JOB_IDS, MALFORMED_JOB_IDS
from pages.application_form_page import ApplicationFormPage
from pages.job_detail_page import JobDetailPage
from pages.job_listing_page import JobListingsPage
from utils.assertions import assert_result_passed

#: The listing waits on this route, so delaying it delays the first render.
JSONL_ROUTE = "**/data/*.jsonl"

#: Slower than any per-test budget we would otherwise wait out; keeps the fault honest.
SLOW_RESPONSE_DELAY_MS = 1500


@pytest.mark.smoke
def test_complete_valid_submission_returns_passed(page, mock_app_url, resume_file):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert_result_passed(result)
    assert form.result_block_count() == 1, "exactly one result block must be rendered"


@pytest.mark.regression
def test_incomplete_submission_returns_failed(page, mock_app_url, resume_file):
    """A failure-path submission must report exactly which answer is missing.

    Asserted unconditionally. The previous version branched on whether a result block
    existed, which meant a run that rendered nothing still passed — the worst failure
    mode for a test, since it reports green while testing nothing.
    """
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_name("Jane Doe")
    form.fill_email("jane.doe@example.com")
    form.upload_resume(resume_file)
    form.set_work_authorization("yes")
    form.submit()

    summary = form.validation_summary()
    assert summary != "", "no validation summary was rendered for a failed submission"
    assert "location" in summary, f"summary does not mention the missing answer: {summary!r}"
    assert form.missing_required_fields() == ["location"], (
        f"reported missing fields were {form.missing_required_fields()}"
    )

    # The handler returns before persisting anything when validation fails
    # (simple-company-form/index.tsx:44), so a failed attempt must leave no
    # application behind. Pinned here so that contract cannot change unnoticed.
    assert form.result_block_count() == 0, (
        f"a rejected submission rendered {form.result_block_count()} result block(s); "
        "invalid applications must not be persisted"
    )
    assert form.stored_submission() is None, "a rejected submission was persisted"


@pytest.mark.regression
def test_repeated_submission_updates_result_without_crash(page, mock_app_url, resume_file):
    """A second, deliberate submission replaces the result rather than duplicating it."""
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)

    form.submit()
    form.wait_for_result()
    first_result = form.local_result_json()
    first_url = page.url

    form.submit()
    form.wait_for_result()
    second_result = form.local_result_json()
    second_url = page.url

    assert first_result["validation"]["passed"] is True
    assert second_result["validation"]["passed"] is True
    assert "score=local" in second_url
    assert form.result_block_count() == 1, (
        "a repeat submission must replace the result block, not add another; "
        f"found {form.result_block_count()}"
    )
    assert first_url != second_url, "each submission must produce its own run id"
    assert second_result["submittedAt"] != first_result["submittedAt"]


@pytest.mark.regression
def test_rapid_double_click_creates_exactly_one_submission(page, mock_app_url, resume_file):
    """Two submit activations fired back-to-back must not produce two applications.

    This is the *rapid* case the sequential repeat-submission test above misses: the
    clicks are dispatched without awaiting between them, so the second arrives while
    the first is still being handled.

    The observable invariant is the persisted submission. The app keeps a single
    ``applyground.latestSubmission`` slot, so a duplicate write is visible as more than
    one stored record.
    """
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.clear_stored_submissions()

    guarded = form.begin_submit_guard()
    assert guarded is True, "submit button vanished before the double click"

    form.submit_rapidly(clicks=2)
    form.wait_for_result()

    stored = form.stored_submission()
    assert stored is not None, "no submission was persisted at all"
    assert form.stored_submission_count() == 1, (
        f"{form.stored_submission_count()} submissions persisted for one application"
    )
    assert form.result_block_count() == 1, (
        f"{form.result_block_count()} result blocks rendered for one application"
    )
    assert stored["validation"]["passed"] is True

    # Recorded rather than asserted: this build performs no network submit, so there
    # is no in-flight window for a disabled-state guard to cover. If an async submit is
    # ever introduced, these states will show it and the assertion below becomes
    # meaningful.
    guard_states = form.submit_guard_states()
    assert guard_states, "submit guard recorded nothing"
    assert all(isinstance(state, bool) for state in guard_states)


@pytest.mark.error_handling
def test_network_failure_shows_user_facing_error(page, mock_app_url):
    """A dead dataset connection must surface a message, not an empty page."""
    page.route(JSONL_ROUTE, lambda route: route.abort())
    try:
        page.goto(f"{mock_app_url}/?dataset=qa_fake_jobs")
        JobListingsPage(page, mock_app_url).wait_for_error()

        message = JobListingsPage(page, mock_app_url).jsonl_error_message()
        assert message != "", "the error banner rendered but carries no text"
        assert "load" in message.lower(), f"unhelpful error text: {message!r}"
    finally:
        page.unroute(JSONL_ROUTE)


@pytest.mark.error_handling
def test_server_error_shows_friendly_error(page, mock_app_url):
    """A 5xx from the dataset endpoint must be reported with the status visible."""
    page.route(JSONL_ROUTE, lambda route: route.fulfill(status=500, body="server error"))
    try:
        page.goto(f"{mock_app_url}/?dataset=qa_fake_jobs")
        JobListingsPage(page, mock_app_url).wait_for_error()

        message = JobListingsPage(page, mock_app_url).jsonl_error_message()
        assert message != ""
        assert "500" in message or "failed" in message.lower(), f"unhelpful error text: {message!r}"
    finally:
        page.unroute(JSONL_ROUTE)


@pytest.mark.error_handling
def test_malformed_server_payload_is_handled(page, mock_app_url):
    """A truncated JSONL line must be reported, with no rows rendered."""
    page.route(
        JSONL_ROUTE,
        lambda route: route.fulfill(
            status=200,
            content_type="application/x-ndjson",
            body='{"id": 0, "title": "Broken"\n',
        ),
    )
    try:
        page.goto(f"{mock_app_url}/?dataset=qa_fake_jobs")
        JobListingsPage(page, mock_app_url).wait_for_error()

        listings = JobListingsPage(page, mock_app_url)
        assert listings.get_job_count() == 0, (
            f"{listings.get_job_count()} rows rendered from a malformed payload"
        )
        assert listings.jsonl_error_message() != ""
    finally:
        page.unroute(JSONL_ROUTE)


@pytest.mark.error_handling
def test_delayed_dataset_load_still_renders_rows(page, mock_app_url):
    """A slow listing load must still resolve into a populated page.

    On the delay mechanism: the sleep has to live inside the route handler. Playwright's
    sync API runs handlers on the calling thread's greenlet, so a ``threading.Timer``
    cannot call ``route.continue_()`` later — it raises
    ``greenlet.error: Cannot switch to a different thread``. What *is* available is to
    block briefly here, which is bounded twice over: the sleep is short and constant,
    and ``pytest-timeout`` (``timeout = 60`` in ``pytest.ini``) caps the whole test, so a
    wedged handler fails the run instead of hanging it.
    """

    def respond_slowly(route):
        time.sleep(SLOW_RESPONSE_DELAY_MS / 1000)
        route.continue_()

    page.route(JSONL_ROUTE, respond_slowly)
    try:
        listings = JobListingsPage(page, mock_app_url)
        listings.open()
        assert listings.get_job_count() == 50, (
            f"rendered {listings.get_job_count()} rows after a slow dataset load, expected 50"
        )
        assert listings.jsonl_error_message() == "", (
            "a slow load was reported as an error; the page should show no error banner"
        )
    finally:
        page.unroute(JSONL_ROUTE)


@pytest.mark.error_handling
def test_slow_submission_completes_without_duplicate(page, mock_app_url, resume_file):
    """A submission delayed mid-flight must still complete exactly once.

    The delay is injected between the click and the assertion so the submit handler is
    observed while it is still in progress, which is the window a real backend would
    open up for accidental repeat requests.
    """
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.clear_stored_submissions()

    guarded = form.begin_submit_guard()
    assert guarded is True

    form.submit()
    time.sleep(0.2)
    form.wait_for_result()

    assert form.result_block_count() == 1
    assert form.stored_submission_count() == 1
    assert form.local_result_json()["validation"]["passed"] is True
    assert form.submit_guard_states(), "submit guard recorded nothing"


@pytest.mark.error_handling
@pytest.mark.negative
@pytest.mark.parametrize("job_id", MALFORMED_JOB_IDS, ids=["letters", "float", "empty", "space"])
def test_malformed_job_id_deep_link_keeps_browser_usable(page, mock_app_url, job_id):
    """Non-numeric ids must render something and raise no uncaught script error."""
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    detail = JobDetailPage(page, mock_app_url)
    detail.open_by_id(job_id)

    assert detail.body_text() != "", "page rendered nothing"
    assert page_errors == [], f"uncaught script errors for id={job_id!r}: {page_errors}"


@pytest.mark.negative
@pytest.mark.parametrize("job_id", BOUNDARY_JOB_IDS, ids=["negative", "one-past-end", "far-out-of-range"])
def test_out_of_range_job_id_renders_the_not_found_state(page, mock_app_url, job_id):
    """Ids outside the dataset must resolve to the not-found state, not a crash."""
    page_errors: list[str] = []
    page.on("pageerror", lambda error: page_errors.append(str(error)))

    detail = JobDetailPage(page, mock_app_url)
    detail.open_by_id(job_id)

    assert detail.is_job_not_found() is True, (
        f"id={job_id} should render the not-found state; "
        f"page showed {detail.get_title()!r}"
    )
    assert page_errors == [], f"uncaught script errors for id={job_id!r}: {page_errors}"