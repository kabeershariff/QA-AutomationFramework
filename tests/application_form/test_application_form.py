"""Tests for the application form: validation, boundaries, and submission outcomes.

Assertions read the submission result document rather than counting DOM nodes, so a
regression that truncates or mangles input is caught instead of passing.
"""

import pytest

from data.boundary_strings import (
    EMOJI_NAME,
    EMPTY,
    INVALID_PHONE_NUMBERS,
    INVALID_URLS,
    LONG_LOCATION,
    LONG_NAME,
    NULL_LIKE,
    NUMERIC_STRING,
    OVERLONG_LOCATION,
    OVERLONG_NAME,
    SHORT_NAME,
    UNICODE_NAME,
    WHITESPACE_ONLY,
)
from data.emails import INVALID_EMAIL_IDS, INVALID_EMAIL_VALUES, VALID_EMAIL_IDS, VALID_EMAIL_VALUES
from data.resume_files import PDF_BYTES, write_disallowed_resume, write_empty_resume, write_resume
from pages.application_form_page import RESUME_ACCEPTED_EXTENSIONS, ApplicationFormPage
from utils.assertions import assert_result_passed, submitted_field

REQUIRED_FIELDS = {"fullName", "email", "location", "resume", "workAuthorization"}


@pytest.mark.smoke
def test_all_required_fields_missing_lists_every_field(page, mock_app_url):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.submit()

    assert set(form.missing_required_fields()) == REQUIRED_FIELDS, (
        f"summary listed {form.missing_required_fields()}"
    )
    assert form.validation_summary() != ""


@pytest.mark.regression
def test_single_missing_required_field_lists_only_that_field(page, mock_app_url, resume_file):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_name("Jane Doe")
    form.fill_email("jane.doe@example.com")
    form.upload_resume(resume_file)
    form.set_work_authorization("yes")
    form.submit()

    assert form.missing_required_fields() == ["location"], (
        f"expected only 'location' to be reported missing, got {form.missing_required_fields()}"
    )


@pytest.mark.regression
def test_resume_metadata_is_available_after_selection(page, mock_app_url, resume_file):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.upload_resume(resume_file)

    assert form.resume_file_names() == ["resume.pdf"], (
        f"resume was listed as {form.resume_file_names()}"
    )
    metadata = form.resume_metadata_text()
    assert metadata, "no size/type metadata rendered for the resume"
    assert "bytes" in metadata[0], f"metadata text was {metadata[0]!r}"


@pytest.mark.negative
@pytest.mark.parametrize("name", [EMPTY, WHITESPACE_ONLY], ids=["empty", "whitespace-only"])
def test_empty_and_whitespace_names_are_treated_as_missing(page, mock_app_url, resume_file, name):
    """An empty or whitespace-only name is not a supplied answer."""
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file, name=name)
    form.submit()

    assert "fullName" in form.missing_required_fields(), (
        f"name {name!r} was accepted as a supplied value"
    )


@pytest.mark.regression
@pytest.mark.parametrize("name", [NULL_LIKE, NUMERIC_STRING], ids=["null-like", "numeric"])
def test_literal_names_are_not_coerced_or_rejected(page, mock_app_url, resume_file, name):
    """Over-validation is a defect too: a candidate may legitimately be named "12345".

    Pins that defensive-looking literals are accepted **verbatim** rather than being
    dropped as empty or rewritten, which is the over-correction of BUG-005.
    """
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file, name=name)
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert result["validation"]["passed"] is True, (
        f"{name!r} was rejected: {result['validation']['missingRequiredFields']}"
    )
    assert result["candidate"]["fullName"] == name, (
        f"{name!r} was stored as {result['candidate']['fullName']!r}"
    )


@pytest.mark.negative
@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-007: `Phone` is declared `kind=\"tel\"` but `validateRequired` never looks "
        "at it, so arbitrary junk is accepted. Flip to a plain assert once optional "
        "fields are validated."
    ),
)
@pytest.mark.parametrize("phone", INVALID_PHONE_NUMBERS, ids=["letters", "symbols", "over-long"])
def test_optional_phone_rejects_nonsense(page, mock_app_url, resume_file, phone):
    """`Phone` is optional, but an unparseable value must not pass validation silently."""
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.fill_phone(phone)
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert result["validation"]["passed"] is False, (
        f"{phone!r} was accepted as a phone number; see reports/bugs/BUG-007.md"
    )


@pytest.mark.negative
@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-007: `Portfolio or profile URL` is declared `kind=\"url\"` but never "
        "validated. Flip to a plain assert once optional fields are validated."
    ),
)
@pytest.mark.parametrize("url", INVALID_URLS, ids=["not-a-url", "wrong-scheme", "no-host", "whitespace"])
def test_optional_portfolio_url_rejects_nonsense(page, mock_app_url, resume_file, url):
    """`Portfolio or profile URL` is optional but must not accept junk unchallenged."""
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.fill_portfolio(url)
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert result["validation"]["passed"] is False, (
        f"{url!r} was accepted as a URL; see reports/bugs/BUG-007.md"
    )


@pytest.mark.boundary
@pytest.mark.regression
def test_long_text_round_trips_into_the_submission_payload(page, mock_app_url, resume_file):
    """500-character input must survive the round trip byte-for-byte.

    Asserting on the result payload, rather than on the presence of a submit button,
    is what makes a truncation or encoding regression fail.
    """
    name = "A" * 500
    location = "B" * 500

    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_name(name)
    form.fill_email("jane.doe@example.com")
    form.fill_location(location)
    form.upload_resume(resume_file)
    form.set_work_authorization("yes")
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert_result_passed(result)
    assert result["candidate"]["fullName"] == name, (
        f"name round-tripped as {len(result['candidate']['fullName'])} characters, expected 500"
    )
    assert result["candidate"]["location"] == location, (
        f"location round-tripped as {len(result['candidate']['location'])} characters, expected 500"
    )


@pytest.mark.boundary
@pytest.mark.parametrize("name", [UNICODE_NAME, EMOJI_NAME], ids=["accented", "emoji"])
def test_unicode_input_round_trips_into_the_submission_payload(page, mock_app_url, resume_file, name):
    """Accented and emoji input must not be mangled, normalised away, or rejected."""
    location = "São Paulo — Île-de-France"

    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_name(name)
    form.fill_email("jane.doe@example.com")
    form.fill_location(location)
    form.upload_resume(resume_file)
    form.set_work_authorization("yes")
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert_result_passed(result)
    assert result["candidate"]["fullName"] == name, (
        f"{name!r} round-tripped as {result['candidate']['fullName']!r}"
    )
    assert result["candidate"]["location"] == location, (
        f"{location!r} round-tripped as {result['candidate']['location']!r}"
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-003: `Full name` and `Current location` declare no maxlength and no "
        "validation-level bound, so over-long input is accepted verbatim. Flip to a "
        "plain assert once a documented maximum is enforced."
    ),
)
def test_field_length_boundary_probe_is_defined(page, mock_app_url, resume_file):
    """Probe the *upper* boundary: over-long input must be rejected or truncated.

    The suite already pins the low boundary (a 1-character name is accepted). No
    maximum is declared anywhere in the product, so this documents current behaviour:
    1000 characters are accepted verbatim and round-trip unchanged.
    """
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)

    assert form.max_name_length() != -1, (
        "`Full name` declares no maxlength attribute; see reports/bugs/BUG-003.md"
    )

    form.fill_valid_application(resume_file, name=OVERLONG_NAME)
    form.fill_location(OVERLONG_LOCATION)
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert len(result["candidate"]["fullName"]) < len(OVERLONG_NAME), (
        f"{len(OVERLONG_NAME)} characters were accepted and stored verbatim"
    )
    assert len(result["candidate"]["location"]) < len(OVERLONG_LOCATION)


@pytest.mark.regression
def test_optional_fields_can_be_omitted(page, mock_app_url, resume_file):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert_result_passed(result)
    assert submitted_field(result, "phone") == ""
    assert submitted_field(result, "portfolioUrl") == ""


@pytest.mark.smoke
@pytest.mark.negative
def test_invalid_email_format_shows_error(page, mock_app_url, resume_file):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.fill_email("not-an-email")
    form.submit()

    assert form.validation_summary() != ""
    assert "email" in form.missing_required_fields()


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-005: a malformed email is pushed into the same bucket as an absent one, "
        "so the summary reads 'missing required answers' while the field is filled, "
        "and no [data-field-error] / aria-invalid is set on the input. Flip to a "
        "plain assert once invalid input is reported separately."
    ),
)
def test_invalid_email_is_flagged_on_the_field(page, mock_app_url, resume_file):
    """An invalid address must be reported as invalid, not as missing, and be marked."""
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.fill_email("not-an-email")
    form.submit()

    assert form.email_value() == "not-an-email", (
        "fixture assumption: the invalid address should still be in the input"
    )
    assert form.validation_summary().lower().count("invalid") >= 1, (
        f"summary does not describe the value as invalid: {form.validation_summary()!r}"
    )
    assert form.field_error_messages(), (
        "no field-level error was rendered for the rejected email; "
        "see reports/bugs/BUG-005.md"
    )
    assert form.aria_invalid(form.EMAIL_LABEL) == "true", (
        f"the rejected email input is marked aria-invalid={form.aria_invalid(form.EMAIL_LABEL)!r}"
    )


@pytest.mark.regression
@pytest.mark.parametrize(
    "label",
    ["Full name", "Email", "Phone", "Current location", "Resume", "Portfolio or profile URL"],
)
def test_every_field_is_reachable_by_its_label(page, mock_app_url, label):
    """Each input must expose an accessible name via its associated ``<label>``.

    Locating fields by label rather than by ``#field-*`` id means an id rename cannot
    silently break every selector in the suite, and it verifies the label is actually
    associated with its control — an accessibility check that costs nothing extra.
    """
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)

    assert form.has_labelled_field(label) is True, (
        f"expected exactly one input labelled {label!r}"
    )


@pytest.mark.regression
def test_work_authorization_group_exposes_a_legend(page, mock_app_url):
    """A radio group must be labelled by a ``<legend>``, not a bare ``<label>``."""
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)

    legend = form.work_authorization_legend()
    assert legend != "", "the radio group rendered no legend"
    assert "authorized to work" in legend.lower(), f"legend was {legend!r}"


@pytest.mark.regression
def test_whitespace_only_input_is_invalid(page, mock_app_url, resume_file):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_name(WHITESPACE_ONLY)
    form.fill_email("jane.doe@example.com")
    form.fill_location("Remote")
    form.upload_resume(resume_file)
    form.set_work_authorization("yes")
    form.submit()

    assert form.validation_summary() != ""
    assert "fullName" in form.missing_required_fields()


@pytest.mark.regression
@pytest.mark.negative
@pytest.mark.parametrize("email", INVALID_EMAIL_VALUES, ids=INVALID_EMAIL_IDS)
def test_invalid_email_variants_are_rejected(page, mock_app_url, resume_file, email):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.fill_email(email)
    form.submit()

    assert form.validation_summary() != ""
    assert "email" in form.missing_required_fields(), (
        f"{email!r} was accepted as a valid address"
    )


@pytest.mark.regression
def test_email_with_surrounding_spaces_is_normalized(page, mock_app_url, resume_file):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.fill_email("  jane.doe@example.com  ")
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert result["validation"]["passed"] is True
    assert "email" not in result["validation"]["missingRequiredFields"]
    assert result["candidate"]["email"] == "jane.doe@example.com", (
        f"surrounding whitespace was not trimmed: {result['candidate']['email']!r}"
    )


@pytest.mark.boundary
@pytest.mark.parametrize("name", [SHORT_NAME, LONG_NAME], ids=["one-char", "200-char"])
def test_boundary_name_lengths_are_accepted(page, mock_app_url, resume_file, name):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file, name=name)
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert result["validation"]["passed"] is True
    assert result["candidate"]["fullName"] == name


@pytest.mark.boundary
def test_boundary_long_location_is_accepted(page, mock_app_url, resume_file):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.fill_location(LONG_LOCATION)
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert result["validation"]["passed"] is True
    assert result["candidate"]["location"] == LONG_LOCATION


@pytest.mark.boundary
def test_whitespace_only_location_is_missing(page, mock_app_url, resume_file):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.fill_location(WHITESPACE_ONLY)
    form.submit()

    assert form.validation_summary() != ""
    assert "location" in form.missing_required_fields()


@pytest.mark.negative
def test_work_authorization_radio_group_is_required(page, mock_app_url, resume_file):
    """Leaving the radio group untouched must block submission.

    Deliberately does *not* call ``fill_valid_application``, which selects "Yes".
    """
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_name("Jane Doe")
    form.fill_email("jane.doe@example.com")
    form.fill_location("Remote")
    form.upload_resume(resume_file)
    form.submit()

    assert "workAuthorization" in form.missing_required_fields(), (
        f"missing fields were {form.missing_required_fields()}"
    )


@pytest.mark.regression
def test_work_authorization_answer_is_recorded(page, mock_app_url, resume_file):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.set_work_authorization("no")
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert_result_passed(result)
    assert submitted_field(result, "workAuthorization") == "no"


@pytest.mark.regression
def test_confirmation_unchecked_still_passes_validation(page, mock_app_url, resume_file):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.set_confirmation(False)
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert result["validation"]["passed"] is True


@pytest.mark.regression
@pytest.mark.parametrize("email", VALID_EMAIL_VALUES, ids=VALID_EMAIL_IDS)
def test_valid_email_variants_are_accepted(page, mock_app_url, resume_file, email):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.fill_valid_application(resume_file)
    form.fill_email(email)
    form.submit()
    form.wait_for_result()

    result = form.local_result_json()
    assert result["validation"]["passed"] is True, (
        f"{email!r} was rejected; missing={result['validation']['missingRequiredFields']}"
    )
    assert "email" not in result["validation"]["missingRequiredFields"]
    assert result["candidate"]["email"] == email


@pytest.mark.negative
@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-004: the resume input declares accept=\".pdf,.doc,.docx\" but the value is "
        "never checked, so any file is accepted. Flip to a plain assert once the "
        "selection is validated and the failure is announced via the error prop."
    ),
)
def test_disallowed_resume_extension_is_rejected(page, mock_app_url, tmp_path):
    """The resume input advertises `accept=".pdf,.doc,.docx"`; that must be enforced."""
    exe_path = write_disallowed_resume(tmp_path)
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.upload_resume(exe_path)

    assert form.resume_file_names() == [], (
        f"a .exe was accepted as a resume: {form.resume_file_names()}; "
        "see reports/bugs/BUG-004.md"
    )
    assert form.field_error_messages(), (
        "no user-facing message explained why the file was rejected; "
        "see reports/bugs/BUG-004.md"
    )


@pytest.mark.negative
@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-004: no size ceiling exists on the resume, so a zero-byte file is "
        "accepted. Flip to a plain assert once an empty file is rejected."
    ),
)
def test_zero_byte_resume_is_rejected(page, mock_app_url, tmp_path):
    """A correctly-named but empty file must be refused as empty."""
    empty_path = write_empty_resume(tmp_path)
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.upload_resume(empty_path)

    assert form.resume_file_names() == [], (
        "a zero-byte file was accepted as a resume; see reports/bugs/BUG-004.md"
    )


@pytest.mark.regression
def test_accepted_resume_extension_is_listed_with_metadata(page, mock_app_url, tmp_path):
    """The positive half of BUG-004, pinned so a future type check cannot over-block."""
    assert set(RESUME_ACCEPTED_EXTENSIONS) == {".pdf", ".doc", ".docx"}
    pdf_path = write_resume(tmp_path, content=PDF_BYTES)
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.upload_resume(pdf_path)

    assert form.resume_file_names() == ["resume.pdf"]
    assert "bytes" in form.resume_metadata_text()[0]


@pytest.mark.cross_browser
def test_keyboard_activation_submits_form(page, mock_app_url):
    form = ApplicationFormPage(page, mock_app_url)
    form.open(0)
    form.focus(form.SUBMIT)
    form.press(form.SUBMIT, "Enter")

    assert form.validation_summary() != ""
    assert "fullName" in form.missing_required_fields()