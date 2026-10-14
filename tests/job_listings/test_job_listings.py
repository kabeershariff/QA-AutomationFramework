"""High-priority tests for the job listings page.

Expected counts are derived from the bundled dataset (``utils.datasets``) rather than
hard-coded, and compared with auto-retrying ``expect`` assertions so a filter change
cannot be read mid-re-render.
"""

import pytest
from playwright.sync_api import expect

from pages.job_detail_page import JobDetailPage
from pages.job_listing_page import JobListingsPage
from utils.assertions import assert_non_empty_strings
from utils.datasets import (
    DEFAULT_DATASET_ID,
    LISTING_PAGE_SIZE,
    QA_FAKE_DATASET_ID,
    experience_label,
    jobs_with_level,
    load_dataset,
    salary_label,
)


@pytest.mark.smoke
@pytest.mark.regression
def test_job_listings_display_required_fields(page, app_url, jobs_dataset):
    """The default listing must render the first page of the dataset, fully populated."""
    listings = JobListingsPage(page, app_url)
    listings.open()

    assert listings.get_job_count() == LISTING_PAGE_SIZE, (
        f"expected the first page of {len(jobs_dataset)} rows "
        f"({LISTING_PAGE_SIZE} per page), rendered {listings.get_job_count()}"
    )
    assert len(listings.job_titles()) == listings.get_job_count()
    assert len(listings.job_levels()) == listings.get_job_count()
    assert len(listings.job_excerpts()) == listings.get_job_count()
    assert_non_empty_strings(listings.job_titles())
    assert_non_empty_strings(listings.job_levels())
    assert_non_empty_strings(listings.job_excerpts())

    first_page_titles = listings.job_titles()
    assert first_page_titles == [job["title"] for job in jobs_dataset[:LISTING_PAGE_SIZE]], (
        "the listing page must show the dataset's first page in file order"
    )


@pytest.mark.regression
def test_index_status_reports_the_full_dataset_size(page, app_url, jobs_dataset):
    listings = JobListingsPage(page, app_url)
    listings.open()

    status = listings.index_status()
    assert f"1-{LISTING_PAGE_SIZE} of {len(jobs_dataset)}" in status, (
        f"index status {status!r} does not report 1-{LISTING_PAGE_SIZE} of {len(jobs_dataset)}"
    )


@pytest.mark.regression
def test_job_listings_level_filter_narrows_to_the_dataset_count(page, app_url):
    """Selecting a level must reduce the result set to exactly the matching records.

    The dataset contains 2 `junior` records out of 1000, so both the count and the
    rendered labels are deterministic.
    """
    expected = jobs_with_level("junior")
    assert len(expected) == 2, "fixture assumption broken: junior count changed"

    listings = JobListingsPage(page, app_url)
    listings.open()
    assert listings.get_job_count() == LISTING_PAGE_SIZE

    listings.filter_by_level("junior")

    expect(listings.get_job_cards()).to_have_count(len(expected))
    assert listings.get_selected_level() == "junior"
    assert listings.job_levels() == [job["job_level"] for job in expected], (
        f"cards reported levels {listings.job_levels()}, expected all 'junior'"
    )


@pytest.mark.regression
def test_clearing_the_level_filter_restores_the_first_page(page, app_url, jobs_dataset):
    listings = JobListingsPage(page, app_url)
    listings.open()

    listings.filter_by_level("junior")
    expect(listings.get_job_cards()).to_have_count(2)

    listings.filter_by_level("all")
    expect(listings.get_job_cards()).to_have_count(LISTING_PAGE_SIZE)
    assert f"of {len(jobs_dataset)}" in listings.index_status()


@pytest.mark.regression
def test_dataset_filter_switches_to_the_selected_dataset(page, app_url):
    fake_jobs = load_dataset(QA_FAKE_DATASET_ID)

    listings = JobListingsPage(page, app_url)
    listings.open()
    assert listings.current_dataset() == DEFAULT_DATASET_ID

    listings.filter_by_dataset(QA_FAKE_DATASET_ID)

    expect(listings.get_job_cards()).to_have_count(len(fake_jobs))
    assert listings.job_titles() == [job["title"] for job in fake_jobs]
    assert listings.job_salaries() == [salary_label(job) for job in fake_jobs]
    assert listings.job_experiences() == [experience_label(job) for job in fake_jobs]


@pytest.mark.smoke
def test_job_card_link_opens_matching_role(page, app_url, jobs_dataset):
    listings = JobListingsPage(page, app_url)
    listings.open()
    clicked_title = listings.job_titles()[0]

    listings.open_job(0)

    detail = JobDetailPage(page, app_url)
    detail.wait_for_selector(detail.TITLE)
    assert detail.get_title() == clicked_title
    assert detail.get_title() == jobs_dataset[0]["title"]


@pytest.mark.smoke
def test_listing_pagination_pages_through_the_dataset(page, app_url, jobs_dataset):
    """Pagination must cover the dataset exactly once, in pages of PAGE_SIZE."""
    total = len(jobs_dataset)
    listings = JobListingsPage(page, app_url)
    listings.open()

    expected_pages = -(-total // LISTING_PAGE_SIZE)
    assert listings.total_pages() == expected_pages, (
        f"{total} rows at {LISTING_PAGE_SIZE}/page should be {expected_pages} pages, "
        f"pagination shows {listings.pagination_status()!r}"
    )
    assert listings.is_previous_enabled() is False, "Previous must be disabled on page 1"
    assert listings.is_next_enabled() is True

    seen_titles: list[str] = []
    for page_number in range(1, expected_pages + 1):
        assert listings.current_page() == page_number
        seen_titles.extend(listings.job_titles())
        if page_number < expected_pages:
            listings.go_to_next_page()
            expect(listings.get_job_cards()).to_have_count(
                min(LISTING_PAGE_SIZE, total - page_number * LISTING_PAGE_SIZE)
            )

    assert len(seen_titles) == total, (
        f"paging through the dataset visited {len(seen_titles)} of {total} rows"
    )
    assert seen_titles == [job["title"] for job in jobs_dataset], (
        "paging did not visit every dataset record in file order"
    )
    assert listings.is_next_enabled() is False, "Next must be disabled on the last page"


@pytest.mark.regression
def test_listing_rows_expose_ids_matching_the_dataset(page, app_url, jobs_dataset):
    listings = JobListingsPage(page, app_url)
    listings.open()

    ids = listings.job_ids()
    assert len(ids) == LISTING_PAGE_SIZE
    assert ids == [str(job["id"]) for job in jobs_dataset[:LISTING_PAGE_SIZE]], (
        "rendered row ids do not match the dataset's first page"
    )


@pytest.mark.regression
def test_salary_and_experience_render_the_dataset_values(page, mock_app_url):
    """Salary and experience must match the record the card was built from."""
    fake_jobs = load_dataset(QA_FAKE_DATASET_ID)

    listings = JobListingsPage(page, mock_app_url)
    listings.open(QA_FAKE_DATASET_ID)

    salaries = listings.job_salaries()
    experiences = listings.job_experiences()

    assert len(salaries) == listings.get_job_count() == len(fake_jobs)
    assert len(experiences) == listings.get_job_count()
    assert salaries == [salary_label(job) for job in fake_jobs], (
        f"salary pills {salaries} do not match the dataset"
    )
    assert experiences == [experience_label(job) for job in fake_jobs], (
        f"experience pills {experiences} do not match the dataset"
    )
    assert_non_empty_strings(salaries)
    assert_non_empty_strings(experiences)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-006: the 1000-row dataset carries no salary/experience field, but both "
        "pills render unconditionally as a bare 'Salary:' / 'Experience:' label. "
        "Flip to a plain assert once the product guards on presence."
    ),
)
def test_missing_salary_and_experience_are_not_shown_as_empty_pills(page, app_url, jobs_dataset):
    """A record with no salary/experience must not render a valueless pill.

    ``big_company_cs_1000`` has neither field on any of its 1000 records, so the
    current page shows 50 pairs of empty pills, which reads as a rendering fault.
    """
    listings = JobListingsPage(page, app_url)
    listings.open()

    for index in range(LISTING_PAGE_SIZE):
        job = jobs_dataset[index]
        assert job.get("salary") in (None, ""), (
            f"dataset row {job['id']} unexpectedly carries a salary; "
            "this test no longer covers the missing-value path"
        )

    shown_salaries = listings.job_salaries()
    assert all(text.strip() != "Salary:" for text in shown_salaries), (
        f"{sum(1 for t in shown_salaries if t.strip() == 'Salary:')} of {len(shown_salaries)} "
        "cards render a 'Salary:' label with no value; see reports/bugs/BUG-006.md"
    )
    assert all(text.strip() != "Experience:" for text in listings.job_experiences())


@pytest.mark.cross_browser
def test_mobile_viewport_has_no_horizontal_scroll(page, mock_app_url):
    page.set_viewport_size({"width": 390, "height": 844})

    listings = JobListingsPage(page, mock_app_url)
    listings.open(QA_FAKE_DATASET_ID)
    assert listings.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

    detail = JobDetailPage(page, mock_app_url)
    detail.open(0, dataset_id=QA_FAKE_DATASET_ID)
    assert detail.evaluate("document.documentElement.scrollWidth <= window.innerWidth")