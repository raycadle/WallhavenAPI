"""
Wallhaven API v1 Python Wrapper

This module provides a client interface to the Wallhaven.cc API v1.
It enables users to search, retrieve, and download wallpapers,
as well as manage collections.

Author: Ray Cadle
License: MIT
"""

import requests
import os
import random
import string
import time
from enum import Enum
from typing import Tuple, Dict, List, Optional, Union, Any

# ---------- Enums ----------

class Purity(Enum):
    """Defines safety filters for wallpaper content used to filter SFW, sketchy, or NSFW results."""
    sfw = "sfw"
    sketchy = "sketchy"
    nsfw = "nsfw"


class Category(Enum):
    """Defines wallpaper categories for filtering search results."""
    general = "general"
    anime = "anime"
    people = "people"


class Sorting(Enum):
    """Defines sorting options for search results returned by the API."""
    date_added = "date_added"
    relevance = "relevance"
    random = "random"
    views = "views"
    favorites = "favorites"
    toplist = "toplist"


class Order(Enum):
    """Defines the ordering direction for sorting (ascending or descending). Default: desc"""
    desc = "desc"
    asc = "asc"


class TopRange(Enum):
    """Defines time-based ranges used when sorting by 'toplist'."""
    one_day = "1d"
    three_days = "3d"
    one_week = "1w"
    one_month = "1M"
    three_months = "3M"
    six_months = "6M"
    one_year = "1y"


class Color(Enum):
    """Provides a list of predefined color hex codes for filtering wallpapers by dominant color."""
    lonestar = "660000"
    red_berry = "990000"
    guardsman_red = "cc0000"
    persian_red = "cc3333"
    french_rose = "ea4c88"
    plum = "993399"
    royal_purple = "663399"
    sapphire = "333399"
    science_blue = "0066cc"
    pacific_blue = "0099cc"
    downy = "66cccc"
    atlantis = "77cc33"
    limeade = "669900"
    verdun_green = "336600"
    verdun_green_2 = "666600"
    olive = "999900"
    earls_green = "cccc33"
    yellow = "ffff00"
    sunglow = "ffcc33"
    orange_peel = "ff9900"
    blaze_orange = "ff6600"
    tuscany = "cc6633"
    potters_clay = "996633"
    nutmeg_wood_finish = "663300"
    black = "000000"
    dusty_gray = "999999"
    silver = "cccccc"
    white = "ffffff"
    gun_powder = "424153"


class Type(Enum):
    """Defines supported image formats for filtering search results."""
    jpeg = "jpeg"
    jpg = "jpg"
    png = "png"


# ---------- Utilities ----------

class Seed:
    """Utility class for generating random alphanumeric seeds."""
    @staticmethod
    def generate() -> str:
        """
        Generate a random 6-character alphanumeric seed string.

        Returns:
            str: Random seed composed of letters and digits.
        """
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))


# ---------- Exceptions ----------

class RequestsLimitError(Exception):
    """
    Raised when the API request limit (HTTP 429) is exceeded.
    
    Attributes:
        message (str, optional): A custom error message that overrides the default.
        status_code (int): HTTP status code received from the API.
    """
    def __init__(
        self,
        message: Optional[str] = None,
        status_code: int = 429
    ):
        self.status_code = status_code
        default_msg: str = "You have exceeded the requests limit. Please try later."
        super().__init__(message or default_msg)


class ApiKeyError(Exception):
    """
    Raised when an invalid, missing, or unauthorized API key is used.
    
    Attributes:
        message (str, optional): A custom error message that overrides the default.
        status_code (int): HTTP status code received from the API.
    """
    def __init__(
        self,
        message: Optional[str] = None,
        status_code: int = 401
    ):
        self.status_code = status_code
        default_msg: str = "Bad API key. Check it please."
        super().__init__(message or default_msg)


class NoWallpaperError(Exception):
    """
    Raised when no wallpaper with the specified ID exists.

    Attributes:
        wallpaper_id (str): ID of the wallpaper that was not found.
        message (str, optional): A custom error message that overrides the default.
        status_code (int): HTTP status code received from the API.
    """
    def __init__(
        self,
        wallpaper_id: str,
        message: Optional[str] = None,
        status_code: int = 404
    ):
        self.wallpaper_id = wallpaper_id
        self.status_code = status_code
        default_msg: str = f"No wallpaper with id {wallpaper_id}"
        super().__init__(message or default_msg)


class UnhandledException(Exception):
    """
    Raised for any unhandled API errors or unexpected HTTP responses.

    Attributes:
        message (str, optional): A custom error message that overrides the default.
        status_code (int, optional): HTTP status code if available.
    """
    def __init__(
        self,
        message: Optional[str] = None,
        status_code: Optional[int] = None
    ):
        self.status_code = status_code
        default_msg: str = "Something went wrong. Please submit this issue to https://github.com/raycadle/WallhavenAPI/issues."
        super().__init__(message or default_msg)


# ---------- API Client Class ----------

class WallhavenAPI:
    """
    Main interface class for interacting with the Wallhaven.cc API v1.

    This class handles requests, retries on failures, search queries,
    downloads, and account-specific endpoints like collections or settings.

    Attributes:
        api_key (str, optional): Wallhaven API key (optional for some endpoints).
        verify_connection (bool): Whether to verify SSL certificates.
        base_url (str): The base API endpoint URL.
        timeout (tuple of integers): Request timeout settings.
        requestslimit_timeout (tuple of integers, optional): Retry configuration on rate limits.
        proxies (dictionary of strings): HTTP/HTTPS proxy settings.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        verify_connection: bool = True,
        base_url: str = "https://wallhaven.cc/api/v1",
        timeout: Tuple[int, int] = (2, 5),
        requestslimit_timeout: Optional[Tuple[int, int]] = None,
        proxies: Dict[str, str] = None
    ):
        self.api_key = api_key
        self.verify_connection = verify_connection
        self.base_url = base_url
        self.timeout = timeout
        self.requestslimit_timeout = requestslimit_timeout
        self.proxies = proxies or {}

    def _request(
        self,
        to_json: bool,
        **kwargs: Any
    ) -> Union[dict, requests.Response]:
        """
        Internal method to perform HTTP requests with retry and error handling.

        Args:
            to_json (bool): Whether to return the response as JSON.
            **kwargs: Parameters passed to requests.request.

        Returns:
            dict or requests.Response: Parsed JSON response or raw response.

        Raises:
            RequestsLimitError: If rate-limited and retries are exhausted.
            ApiKeyError: If API key is invalid.
            UnhandledException: For all other unexpected issues.
        """
        max_retries = self.requestslimit_timeout[0] if self.requestslimit_timeout else 1
        delay = self.requestslimit_timeout[1] if self.requestslimit_timeout else 0
    
        for attempt in range(max_retries):
            # Add API key to query params if available
            if self.api_key:
                kwargs.setdefault("params", {})["apikey"] = self.api_key
            
            # Apply request configuration
            kwargs.setdefault("timeout", self.timeout)
            kwargs.setdefault("verify", self.verify_connection)
            kwargs.setdefault("proxies", self.proxies)
        
            # Send the request
            try:
                response = requests.request(**kwargs)
            except requests.RequestException as e:
                if attempt == max_retries - 1:
                    raise UnhandledException(message=f"Request failed: {str(e)}")
                time.sleep(delay)
                continue
            
            status_code = response.status_code
        
            # Handle rate limiting (retry if needed)
            if status_code == 429:
                if attempt == max_retries - 1:
                    raise RequestsLimitError(status_code=status_code)
                time.sleep(delay)
                continue
            
            # Handle invalid API key
            if status_code == 401:
                raise ApiKeyError(status_code=status_code)
            
            # Handle 404 (let caller interpret if needed)
            if status_code == 404:
                raise UnhandledException(
                    message=f"404 Not Found for URL: {response.url}",
                    status_code=status_code
                )
            
            # Handle any other non-200 status codes
            if status_code != 200:
                raise UnhandledException(
                    message=f"Unexpected status code {status_code} for URL: {response.url}",
                    status_code=status_code
                )
            
            # Return JSON or raw response
            if to_json:
                try:
                    return response.json()
                except Exception as e:
                    raise UnhandledException(
                        message=f"JSON decode error: {str(e)}",
                        status_code=status_code
                    )
                
            return response
        
        # If somehow loop ends without return or raise, raise generic error
        raise UnhandledException(message="Request failed after all retry attempts.")

    def _raw_request(
        self,
        url: str
    ) -> requests.Response:
        """
        Perform a raw GET request with retry and error handling, respecting client settings.

        Args:
            url (str): The full URL of the resource to download.

        Returns:
            requests.Response: The HTTP response with streamed content.

        Raises:
            RequestsLimitError: If too many requests and retries exhausted.
            UnhandledException: For unexpected HTTP errors.
        """
        max_retries = self.requestslimit_timeout[0] if self.requestslimit_timeout else 1
        delay = self.requestslimit_timeout[1] if self.requestslimit_timeout else 0
        
        for attempt in range(max_retries):
            
            # Send the request
            try:
                response = requests.get(
                    url,
                    stream=True,
                    timeout=self.timeout,
                    verify=self.verify_connection,
                    proxies=self.proxies,
                )
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    if attempt == max_retries - 1:
                        raise RequestsLimitError()
                    time.sleep(delay)
                    continue
                else:
                    raise UnhandledException(
                        message=f"Unexpected status code {response.status_code} for URL: {url}",
                        status_code=response.status_code,
                    )
            except requests.RequestException as e:
                # Network-related errors or connection issues
                if attempt == max_retries - 1:
                    raise UnhandledException(message=f"Request failed: {str(e)}")
                time.sleep(delay)
        
        # If somehow loop ends without return or raise, raise generic error
        raise UnhandledException(message="Failed to download after multiple attempts.")

    def _format_url(
        self,
        *args: Union[str, int]
    ) -> str:
        """
        Build a formatted API endpoint URL by appending path components.

        Args:
            *args (str or int): Path components to join to the base URL.

        Returns:
            str: Full URL to the API endpoint.
        """
        url = self.base_url.rstrip("/") + "/"
        return url + "/".join(map(str, args))

    @staticmethod
    def _category(
        general: bool = True,
        anime: bool = True,
        people: bool = False
    ) -> str:
        """
        Convert category flags to API-compatible string format.

        Args:
            general (bool): Include general wallpapers.
            anime (bool): Include anime wallpapers.
            people (bool): Include people wallpapers.

        Returns:
            str: Category format string, e.g., '110'.
        """
        return f"{int(general)}{int(anime)}{int(people)}"

    @staticmethod
    def _purity(
        sfw: bool = True,
        sketchy: bool = True,
        nsfw: bool = False
    ) -> str:
        """
        Convert purity flags to API-compatible string format.

        Args:
            sfw (bool): Include safe-for-work content.
            sketchy (bool): Include sketchy content.
            nsfw (bool): Include not-safe-for-work content.

        Returns:
            str: Purity format string, e.g., '110'.
        """
        return f"{int(sfw)}{int(sketchy)}{int(nsfw)}"

    @staticmethod
    def _format_dimensions(dims: Union[Tuple[int, int], List[Tuple[int, int]]]) -> str:
        """
        Format a single dimension tuple or a list of tuples into
        a comma-separated string suitable for the API.

        Args:
            dims (tuple of integers or list of tuples of integers):
                A single (width, height) tuple or list of such tuples.

        Returns:
            str: A string formatted as "WxH,WxH,..."
        """
        dims = dims if isinstance(dims, list) else [dims]
        return ",".join(f"{w}x{h}" for w, h in dims)

    def search(
        self,
        q: Optional[str] = None,
        categories: Optional[Union[Category, List[Category]]] = None,
        purities: Optional[Union[Purity, List[Purity]]] = None,
        sorting: Optional[Sorting] = None,
        order: Optional[Order] = None,
        top_range: Optional[TopRange] = None,
        atleast: Optional[Tuple[int, int]] = None,
        resolutions: Optional[Union[Tuple[int, int], List[Tuple[int, int]]]] = None,
        ratios: Optional[Union[Tuple[int, int], List[Tuple[int, int]]]] = None,
        colors: Optional[Color] = None,
        page: Optional[int] = None,
        seed: Optional[str] = None
    ) -> dict:
        """
        Search for wallpapers using various filters and parameters.

        Args:
            q (str, optional): Query string (e.g., keywords or tags).
            categories (list or Category, optional): Categories to include.
            purities (list or Purity, optional): Purity filters (SFW, NSFW, etc.).
            sorting (Sorting, optional): How to sort the results.
            order (Order, optional): Sort direction (asc or desc).
            top_range (TopRange, optional): Time range for toplist sorting.
            atleast (tuple of integers, optional): Minimum resolution (width, height).
            resolutions (tuple of integers or list of tuples of integers, optional): Exact resolutions.
            ratios (tuple of integers or list of tuples of integers, optional): Screen ratios (e.g., 16:9).
            colors (Color, optional): Dominant color to filter by.
            page (int, optional): Page number of results.
            seed (str, optional): Seed for reproducible random results.

        Returns:
            dict: JSON response from Wallhaven API.
        """
        params: Dict[str, str] = {}
        if q: params["q"] = q
        if categories:
            categories = categories if isinstance(categories, list) else [categories]
            params["categories"] = self._category(
                Category.general in categories,
                Category.anime in categories,
                Category.people in categories,
            )
        if purities:
            purities = purities if isinstance(purities, list) else [purities]
            params["purity"] = self._purity(
                Purity.sfw in purities,
                Purity.sketchy in purities,
                Purity.nsfw in purities,
            )
        if sorting: params["sorting"] = sorting.value
        if order: params["order"] = order.value
        if top_range: params["topRange"] = top_range.value
        if atleast: params["atleast"] = f"{atleast[0]}x{atleast[1]}"
        if resolutions: params["resolutions"] = self._format_dimensions(resolutions)
        if ratios: params["ratios"] = self._format_dimensions(ratios)
        if colors: params["colors"] = colors.value
        if page: params["page"] = str(page)
        if seed: params["seed"] = seed

        return self._request(True, method="get", url=self._format_url("search"), params=params)

    def wallpaper(
        self,
        wallpaper_id: str
    ) -> dict:
        """
        Retrieve metadata for a specific wallpaper by ID.

        Args:
            wallpaper_id (str): The unique ID of the wallpaper.

        Returns:
            dict: Metadata about the wallpaper.

        Raises:
            NoWallpaperError: If the wallpaper is not found.
        """
        try:
            return self._request(True, method="get", url=self._format_url("w", wallpaper_id))
        except UnhandledException as e:
            # If the error was due to a 404, convert it to a NoWallpaperError
            if e.status_code == 404:
                raise NoWallpaperError(wallpaper_id)
            raise  # Re-raise other unhandled exceptions

    def is_wallpaper_exists(
        self,
        wallpaper_id: str
    ) -> bool:
        """
        Check if a wallpaper exists on Wallhaven.

        Args:
            wallpaper_id (str): The wallpaper ID to check.

        Returns:
            bool: True if wallpaper exists, False otherwise.
        """
        try:
            self.wallpaper(wallpaper_id)
            return True
        except NoWallpaperError:
            return False

    def download_wallpaper(
        self,
        wallpaper_id: str,
        file_path: Optional[str],
        chunk_size: int = 4096
    ) -> Union[str, bytes]:
        """
        Download wallpaper by ID.

        Args:
            wallpaper_id (str): Wallpaper ID.
            file_path (str, optional): Path where image should be saved. If None, returns binary content.
            chunk_size (int): Stream chunk size.

        Returns:
            str or bytes: Saved path or raw content.
        """
        wallpaper_data = self.wallpaper(wallpaper_id)
        wallpaper = self._raw_request(wallpaper_data["data"]["path"])

        if file_path:
            save_path = os.path.abspath(file_path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in wallpaper.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
            return save_path

        return b"".join(wallpaper.iter_content(chunk_size=chunk_size))

    def tag(
        self,
        tag_id: Union[str, int]
    ) -> dict:
        """
        Retrieve tag details by tag ID.

        Args:
            tag_id (str or int): ID of the tag to retrieve.

        Returns:
            dict: Tag metadata.
        """
        return self._request(
            True,
            method="get",
            url=self._format_url("tag", tag_id)
        )

    def settings(self) -> dict:
        """
        Retrieve account settings (requires valid API key).

        Returns:
            dict: User settings as provided by Wallhaven.

        Raises:
            ApiKeyError: If API key is missing or invalid.
        """
        if self.api_key is None:
            raise ApiKeyError("API key required to retrieve settings.")
        return self._request(
            True,
            method="get",
            url=self._format_url("settings")
        )

    def my_collections(self) -> dict:
        """
        Get personal collections for the current user (requires API key).

        Returns:
            dict: User's collections.

        Raises:
            ApiKeyError: If API key is missing.
        """
        if self.api_key is None:
            raise ApiKeyError("API key required to retrieve collections.")
        return self._request(
            True,
            method="get",
            url=self._format_url("collections")
        )

    def user_collections(
        self,
        user_name: str
    ) -> dict:
        """
        Retrieve public collections of another Wallhaven user.

        Args:
            user_name (str): The username whose collections to fetch.

        Returns:
            dict: Public collections for that user.
        """
        return self._request(
            True,
            method="get",
            url=self._format_url("collections", user_name)
        )

    def collection_wallpapers(
        self,
        user_name: str,
        collection_id: Union[str, int],
        page: Optional[int] = None
    ) -> dict:
        """
        Fetch wallpapers from a specific user's collection.

        Args:
            user_name (str): Username who owns the collection.
            collection_id (str or int): The collection's ID.
            page (int, optional): Page number of results.

        Returns:
            dict: Wallpapers from the collection.
        """
        params = {"page": str(page)} if page is not None else {}
        return self._request(
            True,
            method="get",
            url=self._format_url("collections", user_name, collection_id),
            params=params
        )
