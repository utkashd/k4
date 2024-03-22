from fred import Fred
import os

if __name__ == "__main__":
    fred = Fred(
        log_level="info",
        human_name="Utkash",
        dry_run=True,
        ignore_home_assistant_ssl=os.environ.get("FRED_HA_IGNORE_SSL"),
    )
    fred.start()
