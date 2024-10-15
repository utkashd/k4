import os
from gpt_home import GptHome
from gpt_home.gpt_home import GptHomeDebugOptions
from gpt_home.gpt_home_human import GptHomeHuman

if __name__ == "__main__":
    gpt_home = GptHome(
        gpt_home_human=GptHomeHuman(
            ai_name=os.environ.get("GPT_HOME_AI_NAME") or "GPT_HOME",
            human_name=os.environ.get("GPT_HOME_HUMAN_NAME") or "Human",
        ),
        debug_options=GptHomeDebugOptions(
            is_dry_run=True,
            log_level="warn",
            should_save_requests=True,
            opt_in_to_factoids=False,
            should_save_chat_history=True,
        ),
        ignore_home_assistant_ssl=os.environ.get("GPT_HOME_HA_IGNORE_SSL") or False,
    )
    gpt_home.start()
