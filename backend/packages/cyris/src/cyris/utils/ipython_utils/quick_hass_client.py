"""
This file contains utils for quick debugging/testing stuff in ipython.

In my ~/.ipython/profile_default/ipython_config.py file, I have:

```python
c.InteractiveShellApp.extensions = ["rich"]
```

And then in my ~/.ipython/profile_default/startup/ipython_cyris_startup.py file, I have:
```python
import os
from pathlib import Path

current_working_directory = Path(os.getcwd())

cyris_working_directory = os.path.expanduser("~/src/cyris")

if current_working_directory.samefile(cyris_working_directory):
    from cyris.utils.ipython_utils import hass  # noqa: F401
```
"""

import logging
import os
from urllib.parse import urljoin
from homeassistant_api import Client
import urllib3

log = logging.getLogger("cyris")


def create_hass_client() -> Client:
    """
    Creates a quick Home Assistant client, which is useful for quick testing in ipython
    """
    api_url = urljoin(os.environ["CYRIS_HA_BASE_URL"], "/api")
    hass_token = os.environ["CYRIS_HA_TOKEN"]
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


hass = create_hass_client()  # TODO make this optional for faster ipython startup
print(f"\n\nCreated a Home Assistant API client called hass: {hass=}")
