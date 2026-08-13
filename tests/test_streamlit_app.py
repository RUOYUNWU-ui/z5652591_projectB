"""Acceptance tests for the six-page, precomputed-results Streamlit app.

Run from the project root with::

    python tests/test_streamlit_app.py

These checks execute the app in Streamlit's test runtime. They deliberately do
not call the hosted data loader, VADER, or an optimiser.
"""
from __future__ import annotations

import pathlib
import sys

from streamlit.testing.v1 import AppTest


ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _app() -> AppTest:
    app = AppTest.from_file(str(ROOT / "streamlit_app.py"))
    app.run(timeout=60)
    assert not app.exception
    return app


def test_all_six_pages_open_without_exceptions() -> None:
    """Every page in the investor journey should render from saved artifacts."""
    app = _app()
    pages = [
        "Home",
        "Fund Comparison",
        "Fund Fact Sheet",
        "Allocation Builder",
        "Sentiment Analytics",
        "Robustness Lab",
    ]
    for page in pages:
        app.sidebar.radio[0].set_value(page)
        app.run(timeout=60)
        assert not app.exception, f"{page} raised a Streamlit exception"
        assert app.sidebar.radio[0].value == page


def test_invalid_allocation_is_blocked_with_clear_message() -> None:
    """A blend not summing to 100% must warn instead of simulating/crashing."""
    app = _app()
    app.sidebar.radio[0].set_value("Allocation Builder")
    app.run(timeout=60)
    assert not app.exception
    assert app.number_input

    # Change one of the three default allocations so the total becomes 76.67%.
    app.number_input[0].set_value(10.0)
    app.run(timeout=60)
    warnings = [element.value for element in app.warning]
    assert any("exactly 100%" in message for message in warnings)
    assert not app.exception


if __name__ == "__main__":
    test_all_six_pages_open_without_exceptions()
    print("all six Streamlit pages: PASS")
    test_invalid_allocation_is_blocked_with_clear_message()
    print("invalid allocation guard: PASS")
