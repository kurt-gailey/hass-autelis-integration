"""Host input normalisation.

Users paste all sorts of things into the host field. The one that broke a real install
was a full URL, "http://172.16.20.27": the code built "http://http://172.16.20.27/" and
aiohttp tried to resolve a host named "http" on port 80.
"""

import pytest

from custom_components.autelis_pool import base_url, clean_host


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://172.16.20.27", "http://172.16.20.27/"),   # the reported break
        ("http://172.16.20.27/", "http://172.16.20.27/"),
        ("172.16.20.27", "http://172.16.20.27/"),          # the documented form
        ("172.16.20.27:8080", "http://172.16.20.27:8080/"),  # non-standard port
        ("  172.16.20.27  ", "http://172.16.20.27/"),      # stray whitespace
        ("https://pool.example.com", "https://pool.example.com/"),  # explicit https kept
        ("HTTP://172.16.20.27", "HTTP://172.16.20.27/"),   # scheme case-insensitive
    ],
)
def test_base_url_is_always_well_formed(raw, expected):
    assert base_url(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # A bare IP or ip:port must pass through unchanged, so existing users' entity
        # unique_ids ("autelis 192.168.1.5 pump") do not move under them.
        ("192.168.1.5", "192.168.1.5"),
        ("192.168.1.5:8080", "192.168.1.5:8080"),
        ("http://172.16.20.27", "172.16.20.27"),
        ("http://172.16.20.27/", "172.16.20.27"),
        ("  172.16.20.27  ", "172.16.20.27"),
    ],
)
def test_clean_host_strips_scheme_but_preserves_bare_hosts(raw, expected):
    assert clean_host(raw) == expected
