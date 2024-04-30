from gpt_home import GptHome
import os

from gpt_home.gpt_home import GptHomeDebugOptions

if __name__ == "__main__":
    gpt_home = GptHome(
        ai_name=os.environ.get("GPT_HOME_AI_NAME") or "GPT_HOME",
        human_name=os.environ.get("GPT_HOME_HUMAN_NAME") or "Human",
        ignore_home_assistant_ssl=os.environ.get("GPT_HOME_HA_IGNORE_SSL") or False,
        debug_options=GptHomeDebugOptions(
            is_dry_run=False,
            log_level="warn",
            should_save_requests=True,
            opt_in_to_factoids=False,
        ),
    )
    gpt_home.start()
