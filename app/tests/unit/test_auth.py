"""Auth unit tests."""
import pytest
from app.core.security.hashing import get_password_hash, verify_password
from app.core.security.jwt import create_access_token, decode_token


def test_password_hashing():
    plain = "Secret123!"
    hashed = get_password_hash(plain)
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_encode_decode():
    data = {"sub": 1, "email": "test@example.com", "role": "applicant"}
    token = create_access_token(data)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == 1
    assert payload["email"] == "test@example.com"
