from contextlib import closing
from pathlib import Path

import pytest
from django.core.signals import request_finished
from django.urls import resolve


@pytest.mark.parametrize("urlconf", ["config.urls", "config.urls_portfolio"])
def test_favicon_head_matches_get_headers_without_sending_the_file(rf, settings, tmp_path, monkeypatch, urlconf):
    settings.ROOT_DIR = tmp_path
    asset = tmp_path / "homepage" / "static" / "images" / "favicon.png"
    asset.parent.mkdir(parents=True)
    data = b"synthetic favicon bytes"
    asset.write_bytes(data)

    opened_files = []
    original_open = Path.open

    def track_asset_open(path, *args, **kwargs):
        file = original_open(path, *args, **kwargs)
        if path == asset:
            opened_files.append(file)
        return file

    monkeypatch.setattr(Path, "open", track_asset_open)
    # Closing these RequestFactory responses should not touch database connections.
    monkeypatch.setattr(request_finished, "send", lambda **kwargs: [])
    path = "/favicon.ico"
    # Call the resolved view because the test client strips HEAD bodies itself.
    view = resolve(path, urlconf=urlconf).func

    with closing(view(rf.get(path))) as get_response:
        assert get_response.status_code == 200
        assert b"".join(get_response) == data
        assert get_response["Content-Type"] == "image/png"
        assert get_response["Content-Length"] == str(len(data))
        assert set(get_response["Cache-Control"].split(", ")) == {"max-age=86400", "immutable", "public"}

    with closing(view(rf.head(path))) as head_response:
        assert head_response.status_code == 200
        assert b"".join(head_response) == b""
        for header in ("Content-Type", "Content-Length", "Content-Disposition", "Cache-Control"):
            assert head_response[header] == get_response[header]

    assert opened_files
    assert all(file.closed for file in opened_files)
