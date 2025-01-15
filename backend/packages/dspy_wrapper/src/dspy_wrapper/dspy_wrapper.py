import dspy  # type: ignore[import-untyped]
import os
import logging
from rich.logging import RichHandler
from utils import get_repo_root_directory

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("cyris")


def ask(msg: str) -> list[str]:
    api_key = os.environ.get("CYRIS_OPENAI_API_KEY")
    if not api_key:
        return ["env var `CYRIS_OPENAI_API_KEY` is not defined"]

    os.environ["DSP_NOTEBOOK_CACHEDIR"] = os.path.join(
        get_repo_root_directory(), "dspy_cache"
    )

    dspy.disable_logging()
    dspy.disable_litellm_logging()
    lm = dspy.LM(
        model="openai/gpt-4o-mini",
        model_type="chat",
        api_key=api_key,
        cache=True,
        num_retries=2,
    )
    # lm.history = [] # TODO figure out how to not retain history
    dspy.configure(lm=lm)
    return lm.__call__(messages=[{"role": "user", "content": msg}])
