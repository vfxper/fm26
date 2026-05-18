# Feature: friendly-matches, Property 10: Kick-off time format validation is regex-equivalent
"""
Property-based test for ``FriendlyMatchService._validate_kick_off``.

**Validates: Requirements 13.4, 13.5**

The validator MUST accept exactly those strings that match
:data:`KICK_OFF_REGEX` (``^([01]\\d|2[0-3]):[0-5]\\d$``) — i.e. the 24-hour
``HH:MM`` format with ``HH ∈ [00, 23]`` and ``MM ∈ [00, 59]`` — and MUST
reject every other input by raising ``ValidationError`` with
``http_status == 422``.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from app.services.friendly_match_service import (
    FriendlyMatchService,
    KICK_OFF_REGEX,
    ValidationError,
)


# ──────────────────────────────────────────────────────────────────────────
# Service instance — ``_validate_kick_off`` is a pure helper that does not
# touch the DB session, so passing ``None`` is sufficient.
# ──────────────────────────────────────────────────────────────────────────
SERVICE = FriendlyMatchService(session=None)  # type: ignore[arg-type]


# ──────────────────────────────────────────────────────────────────────────
# Valid inputs: all strings of the form ``f"{HH:02d}:{MM:02d}"`` for
# HH ∈ [0, 23] and MM ∈ [0, 59] are accepted.
# ──────────────────────────────────────────────────────────────────────────
@given(
    hour=st.integers(min_value=0, max_value=23),
    minute=st.integers(min_value=0, max_value=59),
)
@settings(max_examples=100, deadline=None)
def test_valid_kick_off_format_is_accepted(hour: int, minute: int) -> None:
    kick_off = f"{hour:02d}:{minute:02d}"
    # Sanity: the regex itself must match (preserves the property's spec).
    assert KICK_OFF_REGEX.match(kick_off), kick_off
    # No exception means validation passed.
    SERVICE._validate_kick_off(kick_off)


# ──────────────────────────────────────────────────────────────────────────
# Invalid inputs: any string that does NOT match KICK_OFF_REGEX must raise
# ``ValidationError`` with ``http_status == 422``.
# ──────────────────────────────────────────────────────────────────────────
@given(
    bad=st.text().filter(lambda s: not KICK_OFF_REGEX.match(s)),
)
@settings(max_examples=100, deadline=None)
def test_invalid_kick_off_format_is_rejected(bad: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        SERVICE._validate_kick_off(bad)
    assert excinfo.value.http_status == 422
