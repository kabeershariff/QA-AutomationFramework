"""Synthetic boundary and defensive-input values for form and navigation tests.

Each constant is consumed by at least one test; anything unused here is dead weight, so
the module is deliberately small.
"""

# --- text field boundaries -------------------------------------------------
EMPTY = ""
WHITESPACE_ONLY = "   "
NULL_LIKE = "null"
NUMERIC_STRING = "12345"
SHORT_NAME = "A"
LONG_NAME = "A" * 200
UNICODE_NAME = "José Müller"
EMOJI_NAME = "Jane 😀 Doe"
LONG_LOCATION = "B" * 200

#: Values probed against the *upper* length boundary. No maximum is declared anywhere
#: in the product, so these document the defect rather than a rule — see BUG-003.
OVERLONG_NAME = "A" * 1000
OVERLONG_LOCATION = "B" * 1000

# --- optional field negatives ---------------------------------------------
INVALID_URLS = ["not-a-url", "ftp://files.example.com", "http://", " "]
INVALID_PHONE_NUMBERS = ["abc", "++++", "12345678901234567890"]

# --- job id boundaries -----------------------------------------------------
#: Ids inside the 1000-row dataset.
VALID_JOB_IDS = [0, 1, 49, 50, 999]
#: Ids at and past the edges of that dataset; each resolves to the not-found state.
BOUNDARY_JOB_IDS = [-1, 1000, 9999]
#: Non-numeric and empty ids, which must not crash the deep-link route.
MALFORMED_JOB_IDS = ["abc", "1.5", "", " "]