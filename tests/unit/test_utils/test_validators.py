"""Unit tests for validators."""

import pytest
from src.utils.validators import validate_password_strength


def test_validate_password_strength_success():
    """Test password validation with valid password."""
    password = "ValidPass123"
    result = validate_password_strength(password)
    assert result == password


def test_validate_password_strength_too_short():
    """Test password validation with too short password."""
    with pytest.raises(ValueError, match="at least 8 characters"):
        validate_password_strength("Short1")


def test_validate_password_strength_no_uppercase():
    """Test password validation without uppercase."""
    with pytest.raises(ValueError, match="uppercase"):
        validate_password_strength("lowercase123")


def test_validate_password_strength_no_lowercase():
    """Test password validation without lowercase."""
    with pytest.raises(ValueError, match="lowercase"):
        validate_password_strength("UPPERCASE123")


def test_validate_password_strength_no_digit():
    """Test password validation without digit."""
    with pytest.raises(ValueError, match="digit"):
        validate_password_strength("NoDigitsHere")

