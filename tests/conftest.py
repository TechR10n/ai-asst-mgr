"""Pytest configuration and shared fixtures."""

import pytest


@pytest.fixture
def sample_fixture() -> str:
    """Provide a sample fixture for testing.

    Returns:
        A sample string value.
    """
    return "test_value"
