from fred import Fred
import os

if __name__ == "__main__":
    fred = Fred(
        log_level="warn",
        human_name="Utkash",
        dry_run=False,
        ignore_home_assistant_ssl=os.environ.get("FRED_HA_IGNORE_SSL"),
    )
    fred.start()
