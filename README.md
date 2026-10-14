# QA Automation Framework (Python + Playwright + pytest)

Page Object Model (POM) based automation framework for the job application portal.
94 automated cases covering listings, job detail navigation, form validation, submission
behaviour, and error handling.

## Structure

```
.
├── conftest.py                 # shared fixtures (app_url, mock_app_url, resume_file, dataset access)
├── pytest.ini                  # pytest configuration and markers
├── requirements.txt
├── pages/                      # page objects
│   ├── base_page.py
│   ├── job_listing_page.py
│   ├── job_detail_page.py
│   └── application_form_page.py
├── tests/                      # one folder per page/area
│   ├── job_listings/
│   ├── job_details/
│   └── application_form/
├── utils/                      # assertion helpers and JSONL dataset loaders
├── data/                       # emails, boundary strings, resume fixtures
├── tools/                      # diagnostic scripts (bug-evidence capture)
├── mock_site/                  # local Applyground clone with extended job fields
└── reports/                    # test results, artifacts, and bug reports
```

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium firefox webkit
```

Build the local copy of the portal that the suite runs against:

```bash
cd mock_site
npm install
npm run build
cd ..
```

The suite serves `mock_site/dist` on http://127.0.0.1:8765 and starts it automatically,
so `pytest` can be run right after the build. A manually started preview server on the
same port is picked up as well:

```bash
npm run preview --prefix mock_site -- --port 8765 --host 127.0.0.1
```

**Target identity is verified.** Before any test runs, the `mock_app_url` fixture fetches
`/data/manifest.json` and refuses to proceed unless the response is this repository's
build. If something else is bound to port 8765 the run fails with
`Refusing to run against <url>` instead of silently producing green results against an
unknown application.

## Running tests

```bash
pytest
```

`pytest.ini` configures the run with `--basetemp=.pytest_tmp`, a repository-local
temporary directory, and a 60-second per-test timeout, so the default command works
without extra options and cannot hang.

Target one area:

```bash
pytest tests/job_listings
pytest tests/job_details
pytest tests/application_form
```

Headed mode:

```bash
pytest --headed
```

Marker selection:

```bash
pytest -m "smoke"           # 10 highest-value journeys
pytest -m "cross_browser"   # 4 compatibility checks
pytest -m "regression"
pytest -m "negative"
pytest -m "boundary"
pytest -m "error_handling"
```

Cross-browser matrix (13 tests x 3 engines):

```bash
pytest -m "smoke or cross_browser" --browser chromium --browser firefox --browser webkit
```

Markers:

| Marker | Purpose |
|---|---|
| `smoke` | Highest-value end-to-end journeys |
| `regression` | Behaviour that must not change |
| `negative` | Inputs that must be rejected |
| `boundary` | Length, size, and range edges |
| `cross_browser` | Engine-specific compatibility checks |
| `error_handling` | Network faults and malformed payloads |

`--strict-markers` is enabled, so a misspelled marker fails the run instead of silently
dropping the test out of `-m` selection.

### Expected failures

13 tests are marked `xfail(strict=True)`. Each one is an **executable guard for a filed
defect**, listed in `reports/test_results.md`. When the underlying bug is fixed, the case
turns into a hard failure rather than passing unnoticed — at which point the `xfail`
marker is deleted and the assertion kept.

To see them separately:

```bash
pytest -rxX
```

### Target of this suite

Every test runs against the local portal copy in `mock_site`. No test submits to the
deployed instance, because `qa_task.txt.txt` prohibits submitting fake applications to
the live portal. `reports/bugs/BUG-001.md` is a defect that only reproduces on the
deployed build; it is filed and retested manually rather than automated.

## Regenerating bug evidence

```bash
python tools/capture_bug_evidence.py
```

Re-drives BUG-002 through BUG-006 in Chromium against `mock_site/dist`, writes
screenshots to `reports/bugs/evidence/`, and prints the probe values quoted in the bug
reports. Diagnostic aid — not part of the pytest suite.

## Documentation

- `build.md` holds the prioritized test plan, the test-case catalog, the page
  object contract, and the phased build status.
- `reports/test_results.md` holds the latest run commands, counts, cross-browser
  matrix, and defect summary.
- `reports/bugs/` holds the individual bug reports and their retest notes.
- `issues.md` is the code-level defect log driving this work, with per-item status.

## Latest results

Run of 2026-10-14, Chromium 1280x720:

| Run | Command | Result |
|---|---|---|
| Full suite | `pytest` | **81 passed, 13 xfailed** (13 xfails are the filed-defect guards) in 91.81s |
| Cross-browser matrix | `pytest -m "smoke or cross_browser" --browser chromium --browser firefox --browser webkit` | **39 passed** (13 tests x 3 engines) in 55.39s |
| Collection | `pytest --collect-only` | 94 tests |

There are no unexpected failures, errors, or skips. Detailed results:
`reports/test_results.md`.

## Test areas

| Area | Collected | Passed | Expected failures |
|---|---|---|---|
| Job listings | 11 | 10 | 1 |
| Job details | 11 | 10 | 1 |
| Application form validation | 56 | 45 | 11 |
| Submission and error handling | 16 | 16 | 0 |
| **Total** | **94** | **81** | **13** |

## Open defects

Seven defects are filed in `reports/bugs/`:

| ID | Severity | Summary |
|---|---|---|
| BUG-001 | Major | Deployed build accepts malformed email formats (manual-only repro) |
| BUG-002 | Major | Application form accepts submissions for a non-existent job id |
| BUG-003 | Major | No maximum length on name or location |
| BUG-004 | Major | Resume `accept` list declared but never enforced; no size ceiling |
| BUG-005 | Major | Invalid email reported as "missing"; no field error or `aria-invalid` |
| BUG-006 | Minor | Empty `Salary:` / `Experience:` pills on datasets lacking those fields |
| BUG-007 | Minor | Optional `phone` and `portfolioUrl` declare a type but are never validated |

## Notes

- Tests run against the copy of the portal kept in this repository (`mock_site`), which
  is modified for the scope of this work (override with `MOCK_BASE_URL`).
- No test submits to the deployed instance. Submission scenarios all use the local copy.
- The local mock auto-starts from `mock_site/dist` when available.
- Set `HEADLESS=false` for headed execution and `SLOW_MO` for action delay.
- Page objects inherit from `BasePage` and own every selector in the suite. Tests call
  page-object methods; the only direct `page` access left is for accessibility probes
  that deliberately exercise accessible names (`get_by_label`, `get_by_role`).
- Expected values are derived from the bundled JSONL datasets (`utils/datasets.py`)
  rather than hard-coded, so a data change surfaces as a clear diff.