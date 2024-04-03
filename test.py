from fred import Fred
import os

from fred.fred import FredDebugOptions

if __name__ == "__main__":
    fred = Fred(
        ai_name=os.environ.get("FRED_AI_NAME") or "Fred",
        human_name=os.environ.get("FRED_HUMAN_NAME") or "Human",
        ignore_home_assistant_ssl=os.environ.get("FRED_HA_IGNORE_SSL") or False,
        debug_options=FredDebugOptions(
            is_dry_run=False,
            log_level="warn",
            should_save_requests=True,
        ),
    )
    fred.start()
