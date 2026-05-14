import pytest
from formatting import isLocalBaseUrl


# --- isLocalBaseUrl ---

def test_isLocalBaseUrl_localhost():
    assert isLocalBaseUrl("http://localhost:1234/v1") is True

def test_isLocalBaseUrl_127():
    assert isLocalBaseUrl("http://127.0.0.1:1234/v1") is True

def test_isLocalBaseUrl_ipv6_loopback():
    assert isLocalBaseUrl("http://[::1]:1234/v1") is True

def test_isLocalBaseUrl_all_interfaces():
    assert isLocalBaseUrl("http://0.0.0.0:1234/v1") is True

def test_isLocalBaseUrl_remote_openai():
    assert isLocalBaseUrl("https://api.openai.com/v1") is False

def test_isLocalBaseUrl_remote_arbitrary():
    assert isLocalBaseUrl("https://example.com/v1") is False
