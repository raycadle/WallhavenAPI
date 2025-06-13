"""
Wallhaven API v1 Python Wrapper

This module provides a client interface to the Wallhaven.cc API v1. It enables
users to search, retrieve, and download wallpapers, as well as manage collections.

Author: Ray Cadle
License: MIT
"""

import requests
import os
import random
import string
import time
from enum import Enum
from typing import Tuple, Dict, List, Optional, Union

# ---------- Enums ----------

class Purity(Enum):
    """Defines safety filters for wallpaper content."""
    sfw = "sfw"
    sketchy = "sketchy"
    nsfw = "nsfw"


class Category(Enum):
    """Defines wallpaper categories."""
    general = "general"
    anime = "anime"
    people = "people"


class Sorting(Enum):
    """Defines sorting options for search results."""
    date_added = "date_added"
    relevance = "relevance"
    random = "random"
    views = "views"
    favorites = "favorites"
    toplist = "toplist"


class Order(Enum):
    """Defines ordering direction for sorting."""
    # Default: desc
    desc = "desc"
    asc = "asc"


class TopRange(Enum):
    """Defines time ranges for the 'toplist' sorting."""
    one_day = "1d"
    three_days = "3d"
    one_week = "1w"
    one_month = "1M"
    three_months = "3M"
    six_months = "6M"
    one_year = "1y"


class Color(Enum):
    """Color hex codes for dominant color filtering in search."""
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
    """Defines supported image formats."""
    jpeg = "jpeg"
    jpg = "jpg"
    png = "png"


# ---------- Utilities ----------

class Seed:
    """Utility class for generating random seeds."""

    @staticmethod
    def generate() -> str:
        """Generate a random 6-character alphanumeric seed."""
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))


# ---------- Exceptions ----------

class RequestsLimitError(Exception):
    """Raised when the API request limit is exceeded."""
    def __init__(self):
        super().__init__("You have exceeded requests limit. Please try later.")


class ApiKeyError(Exception):
    """Raised when an invalid API key is used."""
    def __init__(self):
        super().__init__("Bad api key. Check it please.")


class UnhandledException(Exception):
    """Raised for unhandled API errors."""
    def __init__(self):
        super().__init__("Something went wrong. Please submit this issue to https://github.com/raycadle/WallhavenAPI/issues.")


class NoWallpaperError(Exception):
    """Raised when a wallpaper with the given ID does not exist."""
    def __init__(self, wallpaper_id: str):
        super().__init__(f"No wallpaper with id {wallpaper_id}")


# ---------- API Client Class ----------

class WallhavenAPI:
    """
    Main interface for interacting with the Wallhaven.cc API v1.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        verify_connection: bool = True,
        base_url: str = "https://wallhaven.cc/api/v1",
        timeout: Tuple[int, int] = (2, 5),
        requestslimit_timeout: Optional[Tuple[int, int]] = None,
        proxies: Dict[str, str] = {}
    ):

        """
        Initialize the API wrapper.

        Args:
            api_key (str, optional): Your Wallhaven API key.
            verify_connection (bool): SSL verification for requests.
            base_url (str): API base URL.
            timeout (tuple): (connect_timeout, read_timeout).
            requestslimit_timeout (tuple, optional): (max_retries, delay_in_seconds).
            proxies (dict): Dictionary of HTTP proxies.
        """

        self.verify_connection = verify_connection
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.requestslimit_timeout = requestslimit_timeout
        self.proxies = proxies

    def _request(self, to_json: bool, **kwargs) -> Union[dict, requests.Response]:
        """Internal method to wrap API requests and handle errors."""

        for i in range(self.requestslimit_timeout[0] if self.requestslimit_timeout else 1):
            if self.api_key:
                kwargs.setdefault("params", {})["apikey"] = self.api_key

            kwargs.setdefault("timeout", self.timeout)
            kwargs.setdefault("verify", self.verify_connection)
            kwargs.setdefault("proxies", self.proxies)

            response = requests.request(**kwargs)

            if response.status_code == 429:
                if not self.requestslimit_timeout or i == self.requestslimit_timeout[0] - 1:
                    raise RequestsLimitError
                time.sleep(self.requestslimit_timeout[1])
                continue

            if response.status_code == 401:
                raise ApiKeyError

            if response.status_code != 200:
                raise UnhandledException

            if to_json:
                try:
                    return response.json()
                except:
                    raise UnhandledException

            return response

    def _url_format(self, *args: Union[str, int]) -> str:
        """Build full API endpoint URL."""
        url = self.base_url.rstrip("/") + "/"
        return url + "/".join(map(str, args))

    @staticmethod
    def _category(general: bool = True, anime: bool = True, people: bool = False) -> str:
        """Convert category booleans to API format."""
        return f"{int(general)}{int(anime)}{int(people)}"

    @staticmethod
    def _purity(sfw: bool = True, sketchy: bool = True, nsfw: bool = False) -> str:
        """Convert purity booleans to API format."""
        return f"{int(sfw)}{int(sketchy)}{int(nsfw)}"

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
        Perform a wallpaper search.

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
        if resolutions:
            resolutions = resolutions if isinstance(resolutions, list) else [resolutions]
            params["resolutions"] = ",".join([f"{w}x{h}" for w, h in resolutions])
        if ratios:
            ratios = ratios if isinstance(ratios, list) else [ratios]
            params["ratios"] = ",".join([f"{w}x{h}" for w, h in ratios])
        if colors: params["colors"] = colors.value
        if page: params["page"] = str(page)
        if seed: params["seed"] = seed

        return self._request(True, method="get", url=self._url_format("search"), params=params)

    def wallpaper(self, wallpaper_id: str) -> dict:
        """Get metadata for a single wallpaper by ID."""
        return self._request(True, method="get", url=self._url_format("w", wallpaper_id))

    def is_wallpaper_exists(self, wallpaper_id: str) -> bool:
        """Check whether a wallpaper exists."""
        return "error" not in self.wallpaper(wallpaper_id)

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
            file_path (str): File path to save image.
            chunk_size (int): Stream chunk size.

        Returns:
            str or bytes: Saved path or raw content.
        """
        wallpaper_data = self.wallpaper(wallpaper_id)
        if "error" in wallpaper_data:
            raise NoWallpaperError(wallpaper_id)

        wallpaper = requests.get(
            wallpaper_data["data"]["path"],
            stream=True,
            timeout=self.timeout,
            verify=self.verify_connection,
        )
        if wallpaper.status_code != 200: raise UnhandledException

        if file_path:
            save_path = os.path.abspath(file_path)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in wallpaper.iter_content(chunk_size):
                    f.write(chunk)
            return save_path

        return wallpaper.content

    def tag(self, tag_id: Union[str, int]) -> dict:
        """Retrieve information for a given tag ID."""
        return self._request(True, method="get", url=self._url_format("tag", tag_id))

    def settings(self) -> Optional[dict]:
        """Get account settings (requires API key)."""
        return None if self.api_key is None else self._request(True, method="get", url=self._url_format("settings"))

    def collections(self, user_name: str) -> dict:
        """Get public collections for a given user."""
        return self._request(True, method="get", url=self._url_format(f"collections/{user_name}"))

    def collection_wallpapers(
        self,
        user_name: str,
        collection_id: Union[str, int],
        page: Optional[int] = None
    ) -> dict:
        """Retrieve wallpapers from a specific collection."""
        return self._request(
            True,
            method="get",
            url=self._url_format(f"collections/{user_name}/{collection_id}"),
            params={"page": str(page)} if page is not None else {}
        )

    def my_collections(self) -> Optional[dict]:
        """Get collections for the current user (requires API key)."""
        return None if self.api_key is None else self._request(True, method="get", url=self._url_format("collections"))
