"""Fixtures shared across the test suite.

Only fixtures live here — pytest injects them, so nothing imports this module
and the double-import trap above does not apply. Plain helpers go in
`tests/helpers.py`.
"""

from __future__ import annotations

import pytest

from pipeline.config import load_city


@pytest.fixture
def hong_kong():
    """The real city config.

    The real one rather than a stub on purpose: a stub would drift out of step
    with the schema and keep passing while the shipped config broke.
    """
    return load_city("hong_kong")
