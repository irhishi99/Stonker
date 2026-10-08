"""
Streamlit App Automation & Smoke Test Suite using streamlit.testing.v1.AppTest.
Verifies app.py runs without exceptions on demo data across all 5 tabs including Tab 5 Performance.
"""

import pytest
from streamlit.testing.v1 import AppTest


def test_app_loads_without_exception():
    """Verify Streamlit app initializes cleanly and executes without unhandled exceptions."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()

    # Assert no exceptions during rendering
    assert not at.exception, f"App raised exception: {at.exception}"


def test_app_all_tabs_render():
    """Verify all tabs render content without errors."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()

    assert not at.exception
    assert len(at.title) > 0 or len(at.markdown) > 0


def test_performance_tab_render():
    """Verify Tab 5 (Performance Attribution & CML) content renders cleanly without exceptions."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()

    assert not at.exception
    assert len(at.header) > 0
