"""
This file contains utils for quick debugging/testing stuff in ipython.

In my ~/.ipython/profile_default/ipython_config.py file, I have:

```python
c.InteractiveShellApp.extensions = ["rich"]
```

And then in my ~/.ipython/profile_default/startup/ipython_fred_startup.py file, I have:
```python
import os
from pathlib import Path

current_working_directory = Path(os.getcwd())

fred_working_directory = os.path.expanduser("~/src/fred")

if current_working_directory.samefile(fred_working_directory):
    from fred.utils import *  # noqa: F403
```
"""

import logging
import os
from urllib.parse import urljoin
from homeassistant_api import Client
import urllib3

log = logging.getLogger("fred")


def create_hass_client() -> Client:
    """
    Creates a quick Home Assistant client, which is useful for quick testing in ipython
    """
    api_url = urljoin(os.environ["FRED_HA_BASE_URL"], "/api")
    hass_token = os.environ["FRED_HA_TOKEN"]
    urllib3.disable_warnings(
        category=urllib3.connectionpool.InsecureRequestWarning  # type: ignore[attr-defined]
    )
    client = Client(
        api_url=api_url,
        token=hass_token,
        verify_ssl=False,
    )
    # client.get_config()  # test the client
    return client


hass = create_hass_client()
print(f"\n\nCreated a Home Assistant API client called hass: {hass=}")
