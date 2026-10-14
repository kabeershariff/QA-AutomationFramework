"""Reusable assertion helpers for tests."""

from __future__ import annotations

from typing import Any


def assert_contains_all(text: str, values: list[str]) -> None:
    lowered = text.lower()
    for value in values:
        assert value.lower() in lowered, f"expected {value!r} in {text!r}"


def assert_one_of(values: list[str], allowed: list[str]) -> None:
    assert all(value in allowed for value in values), (
        f"unexpected values: {values}; allowed: {allowed}"
    )


def assert_non_empty_strings(values: list[str]) -> None:
    assert values, "expected at least one value"
    assert all(isinstance(value, str) and value.strip() for value in values), (
        f"expected non-empty strings, got {values!r}"
    )


def assert_result_passed(result: dict[str, Any]) -> None:
    validation = result.get("validation", {})
    assert validation.get("passed") is True, f"expected a passing result, got {validation!r}"
    assert validation.get("missingRequiredFields") == [], (
        f"expected no missing fields, got {validation.get('missingRequiredFields')!r}"
    )


def assert_result_failed(result: dict[str, Any]) -> None:
    validation = result.get("validation", {})
    assert validation.get("passed") is False, f"expected a failing result, got {validation!r}"
    assert validation.get("missingRequiredFields"), (
        "a failed result must name at least one missing field"
    )


def submitted_field(result: dict[str, Any], name: str) -> Any:
    """Return ``name`` from a submission payload, whichever bucket holds it.

    The app splits form values into ``candidate`` (a fixed list of known identity keys,
    ``submission.ts:33-46``) and ``answers`` (everything else). ``portfolioUrl`` and
    ``workAuthorization``, for instance, are answers rather than candidate fields, so a
    caller must not assume a bucket.
    """
    for bucket in ("candidate", "answers"):
        values = result.get(bucket) or {}
        if name in values:
            return values[name]
    raise KeyError(
        f"{name!r} is absent from the submission payload; "
        f"candidate={sorted(result.get('candidate') or {})}, "
        f"answers={sorted(result.get('answers') or {})}"
    )