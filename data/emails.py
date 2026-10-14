"""Synthetic email addresses for validation tests.

Addresses are declared as ``value -> label`` mappings rather than parallel lists. The
pytest parametrisation ids are then read straight off the labels, so an id can never
drift out of step with the value it names — the failure mode that produced a bug report
labelling the wrong case.

Adding an address means adding its label: a ``value`` without a ``label`` has no entry,
and pytest will surface the mismatch instead of silently relabelling every later case.
"""

#: Addresses the application must accept.
VALID_EMAILS = {
    "user@example.com": "simple",
    "user.name@example.com": "dotted-local-part",
    "user+tag@example.com": "plus-tag",
    "user@sub.example.com": "subdomain",
    "a_b-c.d@example.co.uk": "multi-level-tld",
}

#: Addresses the application must reject, covering empty, whitespace, missing parts,
#: structural damage, and the 254-character upper bound from ``validation.ts:9``.
INVALID_EMAILS = {
    "": "empty",
    " ": "whitespace-only",
    "plainaddress": "plain-address",
    "missing-at.example.com": "missing-at-sign",
    "user@": "missing-local-part",
    "@example.com": "missing-domain",
    "user@example": "missing-tld",
    "user name@example.com": "inner-space",
    "user@@example.com": "double-at-sign",
    "a" * 255 + "@example.com": "over-long",
}

#: Values and ids for ``pytest.mark.parametrize``; both derived from the maps above.
VALID_EMAIL_VALUES = list(VALID_EMAILS)
VALID_EMAIL_IDS = list(VALID_EMAILS.values())
INVALID_EMAIL_VALUES = list(INVALID_EMAILS)
INVALID_EMAIL_IDS = list(INVALID_EMAILS.values())