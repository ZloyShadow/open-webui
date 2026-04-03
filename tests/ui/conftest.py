"""
Pytest configuration for UI tests.
"""

import pytest
from playwright.sync_api import sync_playwright


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "ui: mark test as UI test")
    config.addinivalue_line("markers", "slow: mark test as slow test")
    config.addinivalue_line("markers", "integration: mark test as integration test")


@pytest.fixture(scope="session")
def browser():
    """Create a browser instance for the test session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser):
    """Create a new page for each test function."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True
    )
    page = context.new_page()
    yield page
    context.close()
