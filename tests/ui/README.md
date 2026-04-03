# UI Tests

This directory contains UI automation tests using Playwright.

## Setup

### Install Dependencies

```bash
pip install pytest-playwright
playwright install
```

### Run Tests

```bash
# Run all UI tests
pytest tests/ui/ -v

# Run specific test file
pytest tests/ui/test_security_ui.py -v

# Run with browser visible (not headless)
pytest tests/ui/test_security_ui.py -v --headed

# Run with slow motion to see what's happening
pytest tests/ui/test_security_ui.py -v --slowmo=1000
```

## Test Files

- `test_security_ui.py` - Tests for Security Policies & Alerts feature
- `test_api_logs_ui.py` - Tests for API Logs feature
- `conftest.py` - Pytest fixtures and configuration

## Test Categories

### Accessibility Tests
- Menu visibility
- Navigation
- Keyboard accessibility

### Functional Tests
- Page loading
- Data display
- Form interactions
- Filtering and search

### Integration Tests
- API endpoint calls
- Data persistence

### Responsive Design Tests
- Mobile viewport
- Desktop viewport

## Configuration

Edit `conftest.py` to change:
- Browser type (chromium, firefox, webkit)
- Viewport size
- Headless mode

## Troubleshooting

### Tests fail with timeout
- Increase timeout in individual tests
- Check if application is running on correct port
- Verify test data exists

### Elements not found
- Check if page has loaded completely
- Use `page.wait_for_load_state("networkidle")`
- Verify selectors match actual DOM

### Authentication issues
- Ensure admin user exists
- Check credentials in test configuration
- Verify session cookies are set correctly
