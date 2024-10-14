from functools import cached_property
import json
import sys
import os
import logging
from typing import Any, Literal, Never
from ..gpt_home_api_server.messages import (
    GptHomeSystemMessage,
    Message,
)
from gpt_home.chat_history import ChatHistory
from gpt_home.gpt_home_human import GptHomeHuman
from gpt_home.utils.file_io import get_a_users_directory
import openai
from pydantic import BaseModel
from gpt_home.home_assistant_tool_store import HomeAssistantToolStore
from gpt_home.mutable_tools_agent_executor import MutableToolsAgentExecutor
from gpt_home.mutable_tools_openai_tools_agent import MutableToolsOpenAiToolsAgent
from gpt_home.openai_model import OpenAIModel
from gpt_home.utils.save_llm_prompt import save_chat_create_inputs_as_dict
from langchain_core.pydantic_v1 import SecretStr
from langchain_core.messages import SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)

from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent
from langchain.tools import BaseTool
from rich.logging import RichHandler
from rich import print as rich_print


FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("gpt_home")


class GptHomeDebugOptions(BaseModel):
    log_level: Literal["debug", "info", "warn", "error"] = "info"
    is_dry_run: bool = False
    """
    If True, will not actually call Home Assistant services (but will tell you what we 
    would have called). By default, False
    """
    should_save_requests: bool = False
    """
    Whether to save the contents of the OpenAI API requests to a local file, which is
    useful for debugging. Should only be marked `True` when you're developing.
    Overwrites the existing file, if any.
    """
    requests_filename: str = "tmp/llm_requests.json"
    opt_in_to_factoids: bool = False
    """
    CURRENTLY DOESN'T DO ANYTHING. FACTOIDS IS NOT IMPLEMENTED FOR NOW

    Disabling factoids for now because: there's no limit to how many factoids get
    stored, it seems like many of the factoids aren't that relevant/useful (so maybe I
    should tune the prompt), and most importantly, it makes stopping a chat a bit slow,
    and I want to avoid race conditions for free where possible (IOW, to enable
    factoids wider, I should ensure that there is no race condition issue)

    https://stackoverflow.com/questions/30407352/how-to-prevent-a-race-condition-when-multiple-processes-attempt-to-write-to-and
    """
    should_save_chat_history: bool = True


class GptHome:
    def __init__(
        self,
        gpt_home_human: GptHomeHuman = GptHomeHuman(),
        debug_options: GptHomeDebugOptions = GptHomeDebugOptions(),
        ignore_home_assistant_ssl: str | bool = False,
    ):
        """
        TODO write summary here

        Parameters
        ----------
        ai_name : str, optional
            Set your assistant's name, by default "GptHome"
        human_name : str, optional
            Your name, or how you'd like to be addressed by the assistant. The assistant
            might search for Home Assistant entities using your name. e.g., if you ask
            "turn my lights off," it may decide to search for "turn off <your name>
            light," so you may get better results by using your name if your devices
            include your name. 'Human' by default.
        ignore_home_assistant_ssl : str | bool | None, optional
            If falsy, will not verify Home Assistant's SSL certificate. By default,
            False
        debug_options : DebugOptions, optional
            Configure `log_level`, `is_dry_run`, and `should_save_requests`.
        """
        self.debug_options = debug_options
        self._setup_development_tools()
        self.gpt_home_human = gpt_home_human
        directory_to_load_from_and_save_to = get_a_users_directory(
            self.gpt_home_human.user_id
        )
        log.info("Creating chat_history...")
        self.chat_history = ChatHistory(gpt_home_user=gpt_home_human)
        self.home_assistant_tool_store = HomeAssistantToolStore(
            directory_to_load_from_and_save_to=directory_to_load_from_and_save_to,
            base_url=os.environ["GPT_HOME_HA_BASE_URL"],
            chat_history=self.chat_history,
            dry_run=self.debug_options.is_dry_run,
            verify_home_assistant_ssl=not ignore_home_assistant_ssl,
        )
        log.info("Creating prompt_template...")
        self.tool_calling_prompt_template = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=f"You are a personal AI assistant for {self.gpt_home_human.human_name}. "
                    f"Your name is {self.gpt_home_human.ai_name}. Respond concisely, and "
                    " ask for clarification when necessary."
                    # "When opportune, ask simple questions "
                    # f"to learn more about {self.human_name}'s preferences."
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                # HumanMessage(content="{human_input}"), # TODO understand why I can't
                # do this, which seems much safer than the actual solution (below)
                # ("human", "{factoids}"),
                # message types: Use one of 'human', 'user', 'ai', 'assistant', or 'system'
                ("human", "{human_input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
                # this `agent_scratchpad` is REQUIRED for OpenAI function calling. TODO
                # ensure that agent_scratchpad isn't accidentally left out, because
                # langchain is so shit at writing statically-checkable code
            ]
        )
        log.info("Creating llm...")
        self.tool_calling_llm = ChatOpenAI(
            model=OpenAIModel.GPT_4_1106_PREVIEW,
            # model=OpenAIModel.GPT_3_5_TURBO_0613,  # this mostly works, but sometimes is a little stupid
            api_key=SecretStr(os.environ["GPT_HOME_OPENAI_API_KEY"]),
            temperature=0,  # sean paul disapproves
        )
        # this order is important; the agent and agent executor will need to be able to
        # get tools added to them during an `invoke`, and to do that I need references
        # to the agent and agent executor. so I create a placeholder for tools, create
        # the agent and the executor, and then add at least one tool to them before
        # invoking anything.
        self.tools: list[BaseTool] = []
        log.info("Creating agent and agent_executor...")
        self.agent_executor = MutableToolsAgentExecutor(
            agent=MutableToolsOpenAiToolsAgent(
                runnable=create_openai_tools_agent(
                    llm=self.tool_calling_llm,
                    tools=self.tools,
                    prompt=self.tool_calling_prompt_template,
                ),
            ),
            tools=self.tools,
            verbose=self.is_verbose,
        )
        self.tools.append(
            self.home_assistant_tool_store.get_tool_searcher_tool(self.agent_executor)
        )
        log.info("Adding tools to the agent executor (this may take a few minutes)...")
        self.agent_executor.add_tools(self.tools)

        self.timestamp_to_prompts_sent: dict[str, Any] = {}
        "Request bodies of OpenAI API calls are stored in this dict"

        # one vector store for past conversations
        # one vector store for factoids/conclusions about the master
        # one vector store for tools (APIs)

        self.system_messages_queue: list[GptHomeSystemMessage] = []

        log.info("GptHome is initialized.")

    @cached_property
    def is_verbose(self) -> bool:
        return self.debug_options.log_level in ["debug", "info"]

    def _setup_development_tools(self) -> None:
        if os.environ.get("TOKENIZERS_PARALLELISM") != "true":
            # if the user hasn't set this environment variable, don't overwrite it.
            # otherwise (in here), set it to false to avoid a warning from huggingface
            # https://stackoverflow.com/questions/62691279/how-to-disable-tokenizers-parallelism-true-false-warning
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
        # we have to do this now to avoid some unwanted logging
        logging.basicConfig(
            level=self.debug_options.log_level.upper(),
            format=FORMAT,
            datefmt="[%X]",
            handlers=[RichHandler()],
            force=True,
        )
        if self.debug_options.is_dry_run and not self.is_verbose:
            print(
                f"Bypassing logger to warn you that you may want dry_run=True and log_level='info'. You have {self.debug_options.is_dry_run=} and {self.debug_options.log_level=}"
            )

    def _intro(self) -> None: ...

    def _add_system_message(self, message: str) -> None:
        self.system_messages_queue.append(GptHomeSystemMessage(text=message))

    def get_potentially_relevant_tools(self, human_input: str) -> list[BaseTool]:
        k = 6
        relevant_wrapped_tools = (
            self.home_assistant_tool_store.get_k_relevant_home_assistant_tools(
                f"{self.gpt_home_human.human_name} {human_input}", k=k
            )
        )
        potentially_relevant_tools = [
            relevant_wrapped_tool.hass_tool
            for relevant_wrapped_tool in relevant_wrapped_tools
        ]
        self.chat_history.add_gpt_home_system_message(
            f"Starting with {len(potentially_relevant_tools)} tools:\n{'\n'.join(potentially_relevant_tool.name for potentially_relevant_tool in potentially_relevant_tools)}"
        )
        return potentially_relevant_tools

    def ask_gpt_home(self, human_input: str, chat_id: str = "") -> list[Message]:
        self.chat_history.add_human_message(human_input)

        potentially_relevant_tools = self.get_potentially_relevant_tools(human_input)

        self.agent_executor.add_tools(
            potentially_relevant_tools
        )  # TODO avoid duplicates with existing stuff in there

        try:
            with save_chat_create_inputs_as_dict(
                self.tool_calling_llm.client, self.timestamp_to_prompts_sent
            ):
                response = self.agent_executor.invoke(
                    {
                        "human_input": human_input,
                        "chat_history": self.chat_history.get_chat_history_for_langchain_agent(),
                    }
                )
        except openai.RateLimitError:
            log.exception(
                "OpenAI rate-limited you or you have an OpenAI quota problem. Check your token's usage at https://platform.openai.com/usage."
            )
            response = {"output": "Failed due to an API error. Should I retry?"}
        except Exception as e:
            response = {"output": f"Failed due to an unforeseen issue: {str(e)}"}

        self.chat_history.add_gpt_home_message(response["output"])

        # TODO be smarter about resetting tools?
        self.agent_executor.reset_tools(self.tools)

        return self.chat_history.get_latest_response()

    def _write_requests_to_disk(self) -> None:
        with open(self.debug_options.requests_filename, "w") as requests_file:
            json.dump(self.timestamp_to_prompts_sent, requests_file, indent=4)

    def stop_chatting(self) -> None:
        if self.debug_options.should_save_chat_history:
            self.chat_history.save_chat_history_with_system_messages_to_disk()
        if self.debug_options.should_save_requests:
            self._write_requests_to_disk()
        self.chat_history.clear()

    def start(self) -> Never:
        """
        Starts a chat interface in your terminal. Consumes the terminal. Used for
        debugging, so far.
        """

        import readline  # this improves the terminal UI--input() now ignores arrow keys  # noqa: F401

        rich_print("Type '/quit' to quit and '/help' for all options.")

        ai_intro_message = "What can I do for you?"
        rich_print(f"\n'{self.gpt_home_human.ai_name}': {ai_intro_message}")
        self.chat_history.add_gpt_home_message(ai_intro_message)

        while True:
            human_input = input(f"\n{self.gpt_home_human.human_name}: ")

            if human_input.lower() in ["/quit", "/exit", "quit"]:
                log.info("Shutting down gracefully.")
                self.stop_chatting()
                rich_print(f"\n'{self.gpt_home_human.ai_name}': Goodbye.")
                sys.exit(0)
            elif human_input.lower() in ["/help"]:
                rich_print("'/quit' to quit")  # the rest is just for developing
            elif human_input.lower() in ["/clear_chat"]:
                self.chat_history.clear()
                rich_print("Chat history cleared.")
            elif human_input.lower() in ["/clear"]:
                self.chat_history.clear()
                rich_print("Chat history cleared.")
            else:
                gpt_home_responses = self.ask_gpt_home(human_input)
                for msg in gpt_home_responses:
                    if isinstance(msg, GptHomeSystemMessage):
                        pass  # ignore them because instead we just print them in realtime. See chat_history.py
                    else:
                        rich_print(
                            f"\n[green]{self.gpt_home_human.ai_name}[/green]: {msg.text}"
                        )
