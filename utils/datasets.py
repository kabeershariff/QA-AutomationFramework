"""Loaders for the JSONL job datasets bundled under ``mock_site/public/data``.

Tests assert against *these* records rather than against whatever the page happens to
render, so a rendering regression shows up as a mismatch instead of a tautology.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "mock_site" / "public" / "data"

#: Default dataset used by ``JobDetailPage.open``/``ApplicationFormPage.open``.
DEFAULT_DATASET_ID = "big_company_cs_1000"
#: Three-row synthetic dataset that carries salary/experience metadata.
QA_FAKE_DATASET_ID = "qa_fake_jobs"

#: Rows rendered per listings page (``mock_site/src/pages/Home.tsx:12``).
LISTING_PAGE_SIZE = 50


@lru_cache(maxsize=None)
def load_dataset(dataset_id: str = DEFAULT_DATASET_ID) -> tuple[dict[str, Any], ...]:
    """Return every job record of ``dataset_id``, in file order.

    Raises ``FileNotFoundError`` when the dataset is not bundled, so a missing or
    renamed fixture fails the run instead of quietly yielding an empty suite.
    """
    path = DATA_DIR / f"{dataset_id}.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"dataset {dataset_id!r} not found at {path}")
    jobs: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                jobs.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number} is not valid JSON") from error
    return tuple(jobs)


def job_by_id(job_id: str | int, dataset_id: str = DEFAULT_DATASET_ID) -> dict[str, Any]:
    """Return the single record whose ``id`` equals ``job_id``.

    Raises ``KeyError`` for an id the dataset does not contain, which keeps a typo in a
    test from turning into a silently wrong expectation.
    """
    key = str(job_id)
    for job in load_dataset(dataset_id):
        if str(job.get("id")) == key or str(job.get("custom_id")) == key:
            return job
    raise KeyError(f"{dataset_id} has no job with id {job_id!r}")


def jobs_with_level(level: str, dataset_id: str = DEFAULT_DATASET_ID) -> tuple[dict[str, Any], ...]:
    """Return every record whose ``job_level`` equals ``level``."""
    return tuple(job for job in load_dataset(dataset_id) if job.get("job_level") == level)


def salary_label(job: dict[str, Any]) -> str:
    """Expected listing/detail salary pill text for ``job``."""
    return f"Salary: {job.get('salary', '')}"


def experience_label(job: dict[str, Any]) -> str:
    """Expected listing/detail experience pill text for ``job``."""
    return f"Experience: {job.get('experience', '')}"