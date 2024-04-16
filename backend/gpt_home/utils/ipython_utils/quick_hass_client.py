"""
This file contains utils for quick debugging/testing stuff in ipython.

In my ~/.ipython/profile_default/ipython_config.py file, I have:

```python
c.InteractiveShellApp.extensions = ["rich"]
```

And then in my ~/.ipython/profile_default/startup/ipython_gpt_home_startup.py file, I have:
```python
import os
from pathlib import Path

current_working_directory = Path(os.getcwd())

gpt_home_working_directory = os.path.expanduser("~/src/gpt_home")

if current_working_directory.samefile(gpt_home_working_directory):
    from gpt_home.utils.ipython_utils import hass  # noqa: F401
```
"""

import logging
import os
from urllib.parse import urljoin
from homeassistant_api import Client
import urllib3

log = logging.getLogger("gpt_home")


def create_hass_client() -> Client:
    """
    Creates a quick Home Assistant client, which is useful for quick testing in ipython
    """
    api_url = urljoin(os.environ["GPT_HOME_HA_BASE_URL"], "/api")
    hass_token = os.environ["GPT_HOME_HA_TOKEN"]
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
