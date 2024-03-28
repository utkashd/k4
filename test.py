from fred import Fred
import os

if __name__ == "__main__":
    fred = Fred(
        log_level="info",
        ai_name=os.environ.get("FRED_AI_NAME") or "Fred",
        human_name=os.environ.get("FRED_HUMAN_NAME") or "Human",
        dry_run=False,
        ignore_home_assistant_ssl=os.environ.get("FRED_HA_IGNORE_SSL"),
    )
    fred.start()
