"""Tests for the job detail page.

Assertions resolve against the bundled JSONL source records (``jobs_by_id``) rather
than against the URL the test itself constructed, so a page that renders nothing at
all fails instead of passing.
"""

import pytest

from pages.job_detail_page import JobDetailPage
from pages.job_listing_page import JobListingsPage
from utils.datasets import QA_FAKE_DATASET_ID, experience_label, load_dataset, salary_label

UNKNOWN_JOB_ID = 9999


@pytest.mark.smoke
@pytest.mark.regression
def test_job_detail_shows_title_and_metadata(page, app_url, jobs_by_id):
    detail = JobDetailPage(page, app_url)
    detail.open(0)

    expected = jobs_by_id["0"]
    assert detail.get_title() == expected["title"], (
        f"detail page for id=0 rendered {detail.get_title()!r}, "
        f"dataset says {expected['title']!r}"
    )
    assert detail.get_rendered_job_id() == "0"
    assert detail.get_dataset_and_level() != ""
    assert expected["job_level"] in detail.get_dataset_and_level()
    assert detail.get_description() != ""


@pytest.mark.regression
def test_job_detail_is_deep_linkable(page, app_url, jobs_by_id):
    """A deep link must render the job it names, not merely echo the query string."""
    detail = JobDetailPage(page, app_url)
    detail.open(4)

    assert detail.get_rendered_job_id() == "4"
    assert detail.get_title() == jobs_by_id["4"]["title"], (
        f"deep link to id=4 rendered {detail.get_title()!r}, "
        f"dataset says {jobs_by_id['4']['title']!r}"
    )


@pytest.mark.smoke
def test_apply_button_points_to_embedded_form(page, app_url):
    detail = JobDetailPage(page, app_url)
    detail.open(0)
    assert detail.is_application_form_visible() is True


@pytest.mark.smoke
def test_job_detail_previous_next_navigation(page, app_url, jobs_by_id):
    """Next must land on the following dataset record, not merely on a different title."""
    detail = JobDetailPage(page, app_url)
    detail.open(0)
    first_title = detail.get_title()

    detail.next_job()

    assert detail.get_rendered_job_id() == "1"
    assert detail.get_title() == jobs_by_id["1"]["title"]
    assert detail.get_title() != first_title


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-002: an unknown job id renders the not-found state but still serves a "
        "working application form, so a candidate can submit against a requisition "
        "that does not exist. Flip to a plain assert once the product is fixed."
    ),
)
def test_unknown_job_id_offers_no_application_form(page, app_url):
    """An unknown requisition must not accept applications.

    Expected: the not-found state renders and no submit control exists.
    Actual (BUG-002): the form and its Submit button render regardless, and the
    submission is accepted and scored.
    """
    detail = JobDetailPage(page, app_url)
    detail.open_by_id(UNKNOWN_JOB_ID)

    assert detail.is_job_not_found() is True, (
        f"expected the not-found state for id={UNKNOWN_JOB_ID}, "
        f"page rendered {detail.get_title()!r}"
    )
    assert detail.has_submit_control() is False, (
        "an unknown job id must not expose an application submit control; "
        "see reports/bugs/BUG-002.md"
    )
    assert detail.is_application_form_visible() is False


@pytest.mark.negative
def test_unknown_job_id_names_the_missing_requisition(page, app_url):
    """The not-found message must identify which id failed to resolve.

    This half of the unknown-id behaviour is correct today and is pinned so that a
    future change to the not-found copy cannot degrade it while BUG-002 is fixed.
    """
    detail = JobDetailPage(page, app_url)
    detail.open_by_id(UNKNOWN_JOB_ID)

    message = detail.not_found_message()
    assert message != ""
    assert str(UNKNOWN_JOB_ID) in message, (
        f"not-found message {message!r} does not name the requested id {UNKNOWN_JOB_ID}"
    )


@pytest.mark.regression
def test_job_detail_previous_job_round_trip(page, app_url, jobs_by_id):
    detail = JobDetailPage(page, app_url)
    detail.open(1)
    original_title = detail.get_title()

    detail.next_job()
    detail.previous_job()

    assert detail.get_rendered_job_id() == "1"
    assert detail.get_title() == original_title == jobs_by_id["1"]["title"]


@pytest.mark.smoke
@pytest.mark.cross_browser
def test_browser_history_between_listing_and_detail(page, app_url):
    listings = JobListingsPage(page, app_url)
    listings.open()
    card_title = listings.job_titles()[0]

    listings.open_job(0)
    detail = JobDetailPage(page, app_url)
    detail.wait_for_selector(detail.TITLE)
    assert detail.get_title() == card_title

    page.go_back()
    listings.wait_for_selector(listings.JOB_ROW)

    page.go_forward()
    detail.wait_for_selector(detail.TITLE)
    assert detail.get_title() == card_title, (
        "back/forward through the history must restore the same job"
    )


@pytest.mark.cross_browser
def test_job_detail_survives_a_narrow_viewport(page, app_url):
    """Detail pages are the least-tested route; check they render without sideways scroll."""
    page.set_viewport_size({"width": 390, "height": 844})

    detail = JobDetailPage(page, app_url)
    detail.open(0, dataset_id=QA_FAKE_DATASET_ID)

    assert detail.get_title() != ""
    assert detail.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (
        "job detail overflows horizontally at 390px"
    )


@pytest.mark.regression
def test_mock_job_detail_salary_experience_match_dataset(page, mock_app_url):
    """Salary and experience must render the dataset's own values, with the app's labels."""
    jobs = {str(job["id"]): job for job in load_dataset(QA_FAKE_DATASET_ID)}

    for job_id, expected in jobs.items():
        detail = JobDetailPage(page, mock_app_url)
        detail.open(job_id, dataset_id=QA_FAKE_DATASET_ID)

        assert detail.get_title() == expected["title"], (
            f"id={job_id} rendered {detail.get_title()!r}, expected {expected['title']!r}"
        )
        assert detail.get_salary() == salary_label(expected), (
            f"id={job_id} salary pill was {detail.get_salary()!r}"
        )
        assert detail.get_experience() == experience_label(expected), (
            f"id={job_id} experience pill was {detail.get_experience()!r}"
        )
        assert detail.get_description() != ""


@pytest.mark.regression
def test_detail_route_offers_a_named_submit_control(page, app_url):
    """The detail route's apply section must expose a properly named control.

    Uses the accessible name rather than the ``data-action`` attribute, so a rename of
    either the action or the label shows up here instead of in a selector.
    """
    detail = JobDetailPage(page, app_url)
    detail.open(0)

    assert detail.page.get_by_role("button", name="Submit application").count() == 1
    assert detail.has_submit_control() is True