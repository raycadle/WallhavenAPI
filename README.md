# Wallhaven API v1 Python Wrapper

## Overview

This module provides a Python wrapper for the [Wallhaven.cc API](https://wallhaven.cc/help/api) (v1), enabling users to programmatically search for wallpapers, fetch wallpaper metadata, download images, and interact with user collections.

It is suitable for building custom tools or integrations around the Wallhaven API.

> [!Note]
> This project is unofficial and not affiliated with [Wallhaven.cc](https://wallhaven.cc).
> Use at your own discretion and in accordance with the site's [terms of service](https://wallhaven.cc/about).

[Coverage Reports](https://raycadle.github.io/WallhavenAPI/coverage)

---

## 📦 Installation

This module can be installed from PyPI (recommended), or manually by cloning the repo and moving it to your project's root directory.

If installing manually, be sure to clone the latest release and not the `main` branch. The latest release is identical to that on PyPI.
Additionally, the `requests` library will also need to be installed from PyPI or your preferred method.

* PyPI Install
```bash
pip install wallhavenapi
```

* Manual Install
```bash
git clone --depth=1  https://github.com/raycadle/WallhavenAPI.git && cd WallhavenAPI
pip install -r requirements.txt
```

---

## 🚀 Quick Start

```python
from wallhavenapi import WallhavenAPI, Category, Purity

api = WallhavenAPI(api_key="your_api_key")
results = api.search(q="nature", categories=[Category.general], purities=[Purity.sfw])

# Download a specific wallpaper
wallpaper_id = results["data"][0]["id"]
api.download_wallpaper(wallpaper_id, "wallpaper.jpg")
```

---

## 🐛 Issue Reporting

Report bugs [here](https://github.com/raycadle/WallhavenAPI/issues).

---

## Notes

* All API interaction is wrapped in safe error handling with custom exceptions.
* The wrapper is designed to respect Wallhaven API rate limits if configured via `requestslimit_timeout`.
