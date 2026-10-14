# Test Plan — Job Application Portal

## 1. Purpose

A prioritized plan for verifying a candidate-facing job application portal: browsing
listings, opening a role, completing an application form, and submitting it. The plan
covers the six scope areas defined in the assessment brief and maps each to concrete,
reproducible test scenarios.

## 2. Scope

| Area | Question the area answers |
|---|---|
| Job listings | Are titles, salaries, experience requirements, and descriptions displayed correctly? |
| Navigation | Do job links open the correct role, and does navigation behave predictably? |
| Form validation | Are missing, invalid, whitespace-only, and boundary inputs handled correctly? |
| Submission behaviour | Are success and failure handled, and are duplicate submissions prevented? |
| Error handling | Are network failures, slow responses, invalid data, and server errors survivable? |
| Cross-browser | Which compatibility checks matter most across engines? |

## 3. Test Environment

| Item | Value |
|---|---|
| Target | Local portal instance, `http://127.0.0.1:8765` |
| Datasets | `big_company_cs_1000` (1000 roles), `qa_fake_jobs` (3 roles with salary/experience metadata) |
| Engines | Chromium (primary), Firefox, WebKit |
| Viewports | Desktop 1280x720, mobile 390x844 |
| Framework | Python, pytest, Playwright, Page Object Model |
| Execution control | pytest markers, 60s per-test timeout, screenshot/trace/video on failure |

All submission and error scenarios target the local instance, which keeps expected values
deterministic and leaves any external system untouched.

## 4. Prioritization

| Priority | Meaning |
|---|---|
| P0 | Blocking. A failure here means the portal cannot be used to apply for a role. |
| P1 | High value. Covers a named scope area with realistic candidate behaviour. |
| P2 | Supporting. Edge cases, defensive input, and environment-specific checks. |

P0 concentrates on the shortest path a candidate walks: find a role, open it, complete the
form, submit successfully. P1 covers the failure modes a real candidate will hit. P2 covers
input the portal should survive but that occurs rarely.

## 5. Prioritized Scenarios

### 5.1 Job listings

| ID | Pri | Scenario | Expected result |
|---|---|---|---|
| JL-01 | P0 | Listing renders job cards | Every card shows title, level, and excerpt; no card renders empty |
| JL-02 | P0 | First page shows a full page of rows | Row count equals the page size and matches dataset order |
| JL-03 | P0 | Index summary is accurate | The summary reports the visible range and the total |
| JL-04 | P1 | Job cards expose salary and experience | Both labels render, populated, and match the source record |
| JL-05 | P1 | Level filter narrows results | Selecting a level reduces the set to exactly the matching records |
| JL-06 | P1 | Clearing a filter restores the full set | The first page returns and the summary reverts |
| JL-07 | P1 | Dataset filter switches dataset | Cards, count, and metadata all come from the selected dataset |
| JL-08 | P1 | Pagination covers the dataset | Every page is reachable; paging visits each record once, in order |
| JL-09 | P1 | Pagination boundary controls | Previous disabled on page 1; Next disabled on the last page |
| JL-10 | P2 | Narrow viewport | No horizontal scrolling at 390px |

### 5.2 Navigation

| ID | Pri | Scenario | Expected result |
|---|---|---|---|
| NAV-01 | P0 | Job row link opens the matching role | The opened detail page shows the clicked card's title |
| NAV-02 | P0 | Application form is embedded in the detail page | The form section renders and is usable |
| NAV-03 | P0 | Detail page renders title, level, and description | All three are present and non-empty |
| NAV-04 | P1 | Previous/next navigation | Each control moves to the adjacent dataset record |
| NAV-05 | P1 | Previous/next round trip | Next then Previous returns to the original record |
| NAV-06 | P1 | Deep link to a valid job id | The page renders that specific record, not merely the requested URL |
| NAV-07 | P1 | Browser back and forward | History traversal restores the listing and the same detail page |
| NAV-08 | P1 | Unknown job id | The not-found state renders and names the requested id |
| NAV-09 | P2 | Out-of-range job id | Negative, one-past-end, and far-out-of-range ids render the not-found state |
| NAV-10 | P2 | Malformed job id | Non-numeric, float, empty, and whitespace ids render a usable page with no script error |
| NAV-11 | P2 | Detail page at a narrow viewport | No horizontal scrolling at 390px |

### 5.3 Form validation

| ID | Pri | Scenario | Expected result |
|---|---|---|---|
| AF-01 | P0 | Submit with every required field empty | The summary lists all five required fields |
| AF-02 | P0 | Submit with one required field empty | Only that field is listed |
| AF-03 | P0 | Complete valid submission | Validation passes with no missing fields |
| AF-04 | P0 | Required radio group unselected | The group is reported missing and submission is blocked |
| AF-05 | P1 | Invalid email addresses | All 10 malformed variants are rejected |
| AF-06 | P1 | Valid email addresses | All 5 well-formed variants are accepted |
| AF-07 | P1 | Email with surrounding whitespace | Accepted, and the stored value is trimmed |
| AF-08 | P1 | Whitespace-only name and location | Both treated as unanswered, not as supplied |
| AF-09 | P1 | Very long name and location (500 chars) | Accepted and round-tripped into the payload unchanged |
| AF-10 | P1 | Accented and emoji input | Accepted and round-tripped without mangling or normalization |
| AF-11 | P1 | Literal-but-non-empty names | Values such as `null` or `12345` are stored verbatim, not coerced or rejected |
| AF-12 | P1 | Optional fields omitted | Phone, portfolio, and confirmation may all be left blank |
| AF-13 | P1 | Resume metadata after selection | The file name, type, and size are reported |
| AF-14 | P1 | Disallowed resume extension | Rejected with a user-facing message |
| AF-15 | P1 | Zero-byte resume | Rejected as empty |
| AF-16 | P1 | Accepted resume extension | Accepted and listed with metadata |
| AF-17 | P2 | Non-empty literal name boundaries | A 1-character and a 200-character name are both accepted unchanged |
| AF-18 | P2 | Invalid portfolio URL and phone values | Unparseable values are rejected |
| AF-19 | P2 | Field accessibility | Every input is reachable by its label; the radio group exposes a legend |
| AF-20 | P2 | Named submit control | The submit button resolves by role and accessible name |

### 5.4 Submission behaviour

| ID | Pri | Scenario | Expected result |
|---|---|---|---|
| SUB-01 | P0 | Complete valid submission | A result document renders with validation passed |
| SUB-02 | P0 | Incomplete submission | The exact missing field is named; nothing is persisted |
| SUB-03 | P1 | Sequential repeat submission | The result is replaced rather than duplicated |
| SUB-04 | P1 | Rapid double-click on submit | Two activations fired back-to-back persist exactly one application |
| SUB-05 | P1 | Submission delayed mid-flight | The in-flight submission still completes exactly once |
| SUB-06 | P1 | Result block count | Exactly one result document is rendered per application |
| SUB-07 | P2 | Answer fields are recorded | Submitted values appear in the payload unchanged |
| SUB-08 | P2 | Work authorization answer recorded | The selected option reaches the payload |

### 5.5 Error handling

| ID | Pri | Scenario | Expected result |
|---|---|---|---|
| EH-01 | P1 | Dataset request aborted | A user-facing error banner renders; no crash |
| EH-02 | P1 | Dataset returns HTTP 500 | A friendly message naming the failure renders |
| EH-03 | P1 | Dataset responds slowly | Rows still render, and no error is shown while loading |
| EH-04 | P2 | Malformed JSONL payload | The error banner renders and zero rows are displayed |
| EH-05 | P2 | Uncaught script errors during fault injection | None collected across every error scenario |

### 5.6 Cross-browser

| ID | Pri | Scenario | Expected result |
|---|---|---|---|
| CB-01 | P1 | High-value journeys on all three engines | 13 journeys pass on Chromium, Firefox, and WebKit |
| CB-02 | P1 | Detail route on all three engines | Navigation, history, and form validation covered per engine |
| CB-03 | P2 | Responsive layout on all three engines | No horizontal scrolling at 390px |
| CB-04 | P2 | Keyboard activation of submit | The form submits and the validation summary renders |

## 6. Test Case Catalog

Type: POS positive, NEG negative, BND boundary, NAV navigation, ERR error handling,
CB cross-browser, ACC accessibility.

| ID | Area | Type | Pri | Title |
|---|---|---|---|---|
| JL-01 | Listings | POS | P0 | Listing renders cards with required display fields |
| JL-02 | Listings | POS | P0 | First page holds a full page of dataset rows |
| JL-03 | Listings | POS | P0 | Index summary reports the visible range and total |
| JL-04 | Listings | POS | P1 | Salary and experience match the source record |
| JL-05 | Listings | NEG | P1 | Level filter narrows to the exact matching count |
| JL-06 | Listings | POS | P1 | Clearing the filter restores the first page |
| JL-07 | Listings | POS | P1 | Dataset filter switches the listing source |
| JL-08 | Listings | BND | P1 | Pagination reaches every record exactly once |
| JL-09 | Listings | BND | P1 | Pagination controls disable at the boundaries |
| JL-10 | Listings | POS | P2 | No horizontal scroll at a mobile viewport |
| NAV-01 | Navigation | NAV | P0 | Job row link opens the matching role |
| NAV-02 | Navigation | NAV | P0 | Application form is embedded on the detail page |
| NAV-03 | Navigation | POS | P0 | Detail page renders title, level, and description |
| NAV-04 | Navigation | NAV | P1 | Previous and next open adjacent records |
| NAV-05 | Navigation | NAV | P1 | Previous/next round trip returns to the origin |
| NAV-06 | Navigation | NAV | P1 | Deep link renders the requested record |
| NAV-07 | Navigation | NAV | P1 | Browser back and forward restore both views |
| NAV-08 | Navigation | NEG | P1 | Unknown job id renders the not-found state |
| NAV-09 | Navigation | BND | P2 | Out-of-range job id renders the not-found state |
| NAV-10 | Navigation | BND | P2 | Malformed job id keeps the browser usable |
| NAV-11 | Navigation | POS | P2 | Detail page fits a mobile viewport |
| AF-01 | Form | NEG | P0 | All required fields empty lists every field |
| AF-02 | Form | NEG | P0 | One required field empty lists only that field |
| AF-03 | Form | POS | P0 | Complete valid submission passes validation |
| AF-04 | Form | NEG | P0 | Required radio group unselected is rejected |
| AF-05 | Form | NEG | P1 | Ten invalid email variants are rejected |
| AF-06 | Form | POS | P1 | Five valid email variants are accepted |
| AF-07 | Form | POS | P1 | Surrounding email whitespace is trimmed |
| AF-08 | Form | NEG | P1 | Whitespace-only name and location are unanswered |
| AF-09 | Form | BND | P1 | 500-character input round-trips unchanged |
| AF-10 | Form | BND | P1 | Accented and emoji input round-trips unchanged |
| AF-11 | Form | BND | P1 | Literal names are stored verbatim |
| AF-12 | Form | POS | P1 | Optional fields may be omitted |
| AF-13 | Form | POS | P1 | Resume metadata is reported after selection |
| AF-14 | Form | NEG | P1 | Disallowed resume extension is rejected |
| AF-15 | Form | NEG | P1 | Zero-byte resume is rejected |
| AF-16 | Form | POS | P1 | Accepted resume extension is listed with metadata |
| AF-17 | Form | BND | P2 | One-character and 200-character names are accepted |
| AF-18 | Form | NEG | P2 | Invalid portfolio URL and phone values are rejected |
| AF-19 | Form | ACC | P2 | Every field is reachable by its label |
| AF-20 | Form | ACC | P2 | Submit control resolves by accessible name |
| SUB-01 | Submission | POS | P0 | Complete valid submission returns a passing result |
| SUB-02 | Submission | NEG | P0 | Incomplete submission names the missing field |
| SUB-03 | Submission | POS | P1 | Repeat submission replaces the result |
| SUB-04 | Submission | POS | P1 | Rapid double-click persists one application |
| SUB-05 | Submission | ERR | P1 | Delayed submission completes exactly once |
| SUB-06 | Submission | POS | P1 | Exactly one result document per application |
| SUB-07 | Submission | POS | P2 | Submitted values appear in the payload unchanged |
| SUB-08 | Submission | POS | P2 | Work authorization answer is recorded |
| EH-01 | Error | ERR | P1 | Aborted request shows a user-facing error |
| EH-02 | Error | ERR | P1 | HTTP 500 shows a friendly message |
| EH-03 | Error | ERR | P1 | Slow response still renders rows |
| EH-04 | Error | ERR | P2 | Malformed payload shows an error and no rows |
| EH-05 | Error | ERR | P2 | No uncaught script errors under fault injection |
| CB-01 | Cross-browser | CB | P1 | 13 journeys pass on three engines |
| CB-02 | Cross-browser | CB | P1 | Detail route covered on three engines |
| CB-03 | Cross-browser | CB | P2 | No horizontal scroll on three engines |
| CB-04 | Cross-browser | CB | P2 | Keyboard activation of submit |

**Totals:** 64 scenarios — 20 listings, 11 navigation, 20 form, 8 submission, 5 error
handling, 4 cross-browser.

## 7. Design Principles

| Principle | Application |
|---|---|
| Assert on outcomes, not structure | Results are checked against the submission payload, the rendered record, or an observable count — never by counting controls that exist regardless of behaviour |
| Expectation derived from source data | Titles, counts, salary strings, and level distribution are read from the underlying dataset at runtime, so a data change surfaces as a clear diff |
| No conditional verification | A branch on the presence of the thing under test is avoided; absence is asserted directly |
| Deterministic values | Pagination size, filter counts, and dataset ordering are fixed, so counts are exact rather than bounded |
| Selectors isolated in one layer | All selectors live in page objects; tests call page-object methods |
| Accessible locators by preference | Fields are located by associated label and controls by accessible name, which is both more stable and a free accessibility check |
| Failure artefacts | Screenshots, traces, and video are captured automatically on failure |
| Explicit timeouts | Every test is bounded, so a wedged handler fails the run instead of hanging it |
| Run isolation | Each test starts from a fresh browser context and its own synthetic data |

## 8. Execution

```bash
# Full suite
pytest

# Single area
pytest tests/job_listings
pytest tests/job_details
pytest tests/application_form

# By priority and type
pytest -m "smoke"
pytest -m "negative"
pytest -m "boundary"
pytest -m "error_handling"
pytest -m "cross_browser"

# Cross-browser matrix
pytest -m "smoke or cross_browser" --browser chromium --browser firefox --browser webkit

# Headed mode
pytest --headed

# Expected failures listed explicitly
pytest -rxX
```

## 9. Entry and Exit Criteria

**Entry criteria**

- The portal builds and is reachable at the target address.
- Datasets are present and the manifest resolves.
- All three engines are installed for cross-browser runs.

**Exit criteria**

- All P0 scenarios pass on the primary engine.
- The cross-browser matrix passes on all three engines.
- No unexpected failures, errors, or skips remain.
- Every case marked as an expected failure is tied to a tracked application limitation
  and carries a guard that fails once that limitation is fixed.
- Results, per-engine matrix, and coverage are recorded in the results report.

## 10. Results

Run on Chromium, Firefox, and WebKit.

| Measure | Result |
|---|---|
| Automated cases | 94 collected — 81 passing, 13 expected failures, 0 unexpected failures |
| Wall clock, primary engine | 91.81 s |
| Cross-browser matrix | 13 cases x 3 engines — 39 passing |
| Coverage by area | Listings, navigation, form validation, submission, error handling, cross-browser — all six areas |
| Accessibility checks | Label association for every field, radio legend, named submit control |

Thirteen cases carry expected-failure markers. Each is bound to a known application
limitation and is written so that fixing the limitation turns it into a hard failure —
which keeps the guard visible instead of allowing it to pass unnoticed.

## 11. Risk and Limitations

| Risk | Mitigation |
|---|---|
| Single target instance | The plan targets one deployment; cross-deployment differences are out of scope |
| Metadata-only uploads | File validation scenarios assert what the portal accepts and records, not transfer behaviour |
| Deterministic fixtures | Fixed data makes counts exact; the same data must accompany any re-baselining |
| Coverage ceiling | Keyboard tab-order traversal and automated accessibility auditing remain outside the current scope |