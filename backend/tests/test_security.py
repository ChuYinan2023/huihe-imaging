import pytest
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, hash_token,
)


def test_password_hash_and_verify():
    password = "SecurePass123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)


def test_create_access_token():
    token = create_access_token(user_id=1, role="admin", token_version=1)
    payload = decode_token(token, audience="access")
    assert payload["sub"] == "1"
    assert payload["role"] == "admin"
    assert payload["tv"] == 1
    assert payload["iss"] == "huihe-imaging"
    assert payload["aud"] == "access"


def test_create_refresh_token():
    token, jti, family_id = create_refresh_token(user_id=1, token_version=1)
    payload = decode_token(token, audience="refresh")
    assert payload["sub"] == "1"
    assert payload["aud"] == "refresh"
    assert payload["jti"] == jti
    assert payload["fid"] == family_id


def test_refresh_token_rotation():
    token, jti, family_id = create_refresh_token(user_id=1, token_version=1)
    new_token, new_jti, same_family = create_refresh_token(
        user_id=1, token_version=1, family_id=family_id
    )
    assert same_family == family_id
    assert new_jti != jti


def test_decode_token_wrong_audience():
    token = create_access_token(user_id=1, role="admin", token_version=1)
    with pytest.raises(Exception):
        decode_token(token, audience="refresh")


def test_hash_token():
    token = "some-token-string"
    hashed = hash_token(token)
    assert len(hashed) == 64
    assert hash_token(token) == hashed
