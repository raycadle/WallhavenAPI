import pytest
from pathlib import Path
from typing import Dict, Any
from requests.exceptions import ConnectionError

from wallhavenapi import (
    WallhavenAPI,
    Purity,
    Category,
    Sorting,
    Order,
    TopRange,
    Color,
    Type,
    Seed,
    RequestsLimitError,
    ApiKeyError,
    UnhandledException,
    NoWallpaperError,
)

API_BASE_URL = "https://wallhaven.cc/api/v1"


@pytest.fixture
def api() -> WallhavenAPI:
    """
    Fixture to create and return an instance of the WallhavenAPI
    with a fake API key and request limits for testing.
    """
    return WallhavenAPI(api_key="FAKE_API_KEY", verify_connection=False, requestslimit_timeout=(2, 0.1))


def test_category_and_purity_helpers() -> None:
    """
    Test the static methods _category and _purity to ensure correct
    string conversion based on input booleans.
    """
    assert WallhavenAPI._category(True, False, True) == "101"
    assert WallhavenAPI._purity(False, True, True) == "011"


def test_format_url(api: WallhavenAPI) -> None:
    """
    Test the internal _format_url method to ensure it generates the
    correct endpoint URL.
    """
    url: str = api._format_url("search")
    assert url == f"{API_BASE_URL}/search"


def test_search_success(requests_mock, api: WallhavenAPI) -> None:
    """
    Test the search method for a successful request, asserting that the
    response contains expected keys and data structure.
    """
    endpoint = f"{API_BASE_URL}/search"
    requests_mock.get(endpoint, json={"data": [], "meta": {"current_page": 1}})

    response: Dict[str, Any] = api.search(q="nature", categories=[Category.general], purities=[Purity.sfw])
    assert "data" in response
    assert response["meta"]["current_page"] == 1


def test_request_limit_error(requests_mock, api: WallhavenAPI) -> None:
    """
    Test handling of HTTP 429 Too Many Requests.
    Should raise RequestsLimitError.
    """
    endpoint = f"{API_BASE_URL}/search"
    requests_mock.get(endpoint, status_code=429)

    with pytest.raises(RequestsLimitError):
        api.search()


def test_api_key_error(requests_mock, api: WallhavenAPI) -> None:
    """
    Test handling of HTTP 401 Unauthorized.
    Should raise ApiKeyError.
    """
    endpoint = f"{API_BASE_URL}/search"
    requests_mock.get(endpoint, status_code=401)

    with pytest.raises(ApiKeyError):
        api.search()


def test_unhandled_exception(requests_mock, api: WallhavenAPI) -> None:
    """
    Test handling of unexpected HTTP 500 errors.
    Should raise UnhandledException.
    """
    endpoint = f"{API_BASE_URL}/search"
    requests_mock.get(endpoint, status_code=500)

    with pytest.raises(UnhandledException):
        api.search()


def test_wallpaper_and_existence(requests_mock, api: WallhavenAPI) -> None:
    """
    Test the is_wallpaper_exists method to check if a wallpaper exists
    or not based on API response.
    """
    wallpaper_id: str = "abc123"
    wallpaper_url: str = f"{API_BASE_URL}/w/{wallpaper_id}"

    # Successful case
    requests_mock.get(wallpaper_url, json={"data": {"id": wallpaper_id, "path": "http://example.com/image.jpg"}})
    assert api.is_wallpaper_exists(wallpaper_id)

    # Wallpaper not found case
    requests_mock.get(wallpaper_url, json={"error": "Not found"}, status_code=404)
    assert not api.is_wallpaper_exists(wallpaper_id)


def test_download_wallpaper_success(requests_mock, api: WallhavenAPI, tmp_path: Path) -> None:
    """
    Test the download_wallpaper method to ensure a wallpaper is
    correctly downloaded and saved locally.
    """
    wallpaper_id: str = "abc123"
    wallpaper_url: str = f"{API_BASE_URL}/w/{wallpaper_id}"
    image_url: str = "http://example.com/image.jpg"
    image_content: bytes = b"fakeimagedata"

    requests_mock.get(wallpaper_url, json={"data": {"id": wallpaper_id, "path": image_url}})
    requests_mock.get(image_url, content=image_content)

    file_path: Path = tmp_path / "wallpaper.jpg"
    saved_path: str = api.download_wallpaper(wallpaper_id, str(file_path))
    assert saved_path == str(file_path)
    assert file_path.read_bytes() == image_content


def test_download_wallpaper_no_wallpaper_error(requests_mock, api: WallhavenAPI) -> None:
    """
    Test that download_wallpaper raises NoWallpaperError when the
    wallpaper is not found (HTTP 404).
    """
    wallpaper_id: str = "abc123"
    wallpaper_url: str = f"{API_BASE_URL}/w/{wallpaper_id}"

    requests_mock.get(wallpaper_url, json={"error": "Not found"}, status_code=404)

    with pytest.raises(NoWallpaperError):
        api.download_wallpaper(wallpaper_id, None)


def test_download_wallpaper_to_bytes(requests_mock, api: WallhavenAPI) -> None:
    """
    Ensure that raw wallpaper bytes are returned correctly when no file_path
    is provided to the download_wallpaper method.
    """
    wallpaper_id: str = "abc123"
    wallpaper_url: str = f"{API_BASE_URL}/w/{wallpaper_id}"
    image_url: str = "http://example.com/image.jpg"
    image_content: bytes = b"rawimagebytes"

    requests_mock.get(wallpaper_url, json={"data": {"id": wallpaper_id, "path": image_url}})
    requests_mock.get(image_url, content=image_content)

    content = api.download_wallpaper(wallpaper_id, file_path=None)
    assert isinstance(content, bytes)
    assert content == image_content


def test_seed_generate() -> None:
    """
    Ensure the Seed.generate method returns a 6-character alphanumeric string.
    """
    seed: str = Seed.generate()
    assert isinstance(seed, str)
    assert len(seed) == 6
    assert seed.isalnum()


def test_json_decode_error(monkeypatch, api: WallhavenAPI) -> None:
    """
    Simulate a response with invalid JSON to trigger a JSON decode error
    and ensure that UnhandledException is raised.
    """
    class BadResponse:
        status_code = 200
        url = f"{API_BASE_URL}/search"

        def json(self) -> None:
            raise ValueError("Invalid JSON")

    monkeypatch.setattr("wallhavenapi.wallhavenapi.requests.request", lambda **kwargs: BadResponse())

    with pytest.raises(UnhandledException) as exc_info:
        api.search(q="badjson")
    assert "JSON decode error" in str(exc_info.value)


def test_unexpected_status_code(monkeypatch, api: WallhavenAPI) -> None:
    """
    Simulate a non-429/401/404/500 status code (e.g., 403) and ensure
    UnhandledException is raised correctly.
    """
    class ForbiddenResponse:
        status_code = 403
        url = f"{API_BASE_URL}/search"

        def json(self) -> Dict[str, Any]:
            return {}

    monkeypatch.setattr("wallhavenapi.wallhavenapi.requests.request", lambda **kwargs: ForbiddenResponse())

    with pytest.raises(UnhandledException) as exc_info:
        api.search(q="forbidden")
    assert "Unexpected status code 403" in str(exc_info.value)


def test_raw_request_retry_exhaustion(monkeypatch, api: WallhavenAPI) -> None:
    """
    Simulate a network failure that triggers all retry attempts to fail,
    and ensure an UnhandledException is raised after exhaustion.
    """
    def failing_request(*args: Any, **kwargs: Any) -> Any:
        raise ConnectionError("Network down")

    monkeypatch.setattr("wallhavenapi.wallhavenapi.requests.get", failing_request)

    with pytest.raises(UnhandledException) as exc_info:
        api._raw_request("http://example.com/image.jpg")
    assert "Request failed" in str(exc_info.value)


def test_raw_request_unexpected_status(monkeypatch, api: WallhavenAPI) -> None:
    """
    Simulate an unexpected status code in _raw_request and verify
    UnhandledException is raised appropriately.
    """
    class BadRawResponse:
        status_code = 403
        url = "http://example.com/image.jpg"

        def iter_content(self, chunk_size: int = 4096):
            return iter([b""])

    monkeypatch.setattr("wallhavenapi.wallhavenapi.requests.get", lambda *a, **kw: BadRawResponse())

    with pytest.raises(UnhandledException) as exc_info:
        api._raw_request("http://example.com/image.jpg")
    assert "Unexpected status code 403" in str(exc_info.value)
