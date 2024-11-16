import os
from cyris import Cyris
from cyris.cyris import CyrisDebugOptions
from cyris.cyris_human import CyrisHuman

if __name__ == "__main__":
    cyris = Cyris(
        cyris_human=CyrisHuman(
            ai_name=os.environ.get("CYRIS_AI_NAME") or "CYRIS",
            human_name=os.environ.get("CYRIS_HUMAN_NAME") or "Human",
        ),
        debug_options=CyrisDebugOptions(
            is_dry_run=True,
            log_level="warn",
            should_save_requests=True,
            opt_in_to_factoids=False,
            should_save_chat_history=True,
        ),
        ignore_home_assistant_ssl=os.environ.get("CYRIS_HA_IGNORE_SSL") or False,
    )
    cyris.start()
