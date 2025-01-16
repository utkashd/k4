import os
import logging
from backend_commons.messages import MessageInDb
from rich.logging import RichHandler
from utils import get_repo_root_directory

# The following needs to happen before `dsp` is imported. Great design...
cache_dir = os.path.join(get_repo_root_directory(), "dspy_cache")
os.environ["DSPY_CACHEDIR"] = cache_dir
os.environ["DSP_CACHEDIR"] = cache_dir
os.environ["DSP_NOTEBOOK_CACHEDIR"] = cache_dir

import dspy  # type: ignore[import-untyped]  # noqa: E402

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("cyris")


class Cyris:
    def __init__(self):
        api_key = os.environ.get("CYRIS_OPENAI_API_KEY")
        if not api_key:
            raise Exception("env var `CYRIS_OPENAI_API_KEY` is not defined")

        dspy.disable_logging()
        dspy.disable_litellm_logging()

        self.lm = dspy.asyncify(
            dspy.LM(
                model="openai/gpt-4o-mini",
                model_type="chat",
                api_key=api_key,
                cache=True,
                num_retries=2,
            )
        )
        dspy.configure(lm=self.lm)

    async def ask(
        self, new_msg: MessageInDb, chat_history: list[MessageInDb]
    ) -> list[str]:
        # lm.history = [] # TODO figure out how to not retain history
        history: list[dict[str, str]] = []
        for history_message in chat_history:
            history.append(
                {
                    "role": "user" if history_message.user_id else "assistant",
                    "content": history_message.text,
                }
            )
        history.append({"role": "user", "content": new_msg.text})
        return await self.lm.__call__(messages=history)
