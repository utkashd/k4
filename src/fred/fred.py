import json
import sys
import os
import logging
from typing import Any, Literal, Never, Sequence
import openai
from pydantic import BaseModel

# from fred.vector_store import VectorStore
from fred.home_assistant_tool_store import HomeAssistantToolStore
from fred.mutable_tools_agent_executor import MutableToolsAgentExecutor
from fred.mutable_tools_openai_tools_agent import MutableToolsOpenAiToolsAgent
from fred.openai_model import OpenAIModel
from fred.utils.save_llm_prompt import save_chat_create_inputs_as_dict
import readline  # this improves the terminal UI--input() now ignores arrow keys  # noqa: F401
from langchain_core.pydantic_v1 import SecretStr
from langchain.tools import BaseTool
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent
from rich.logging import RichHandler
from rich import print as rich_print


FORMAT = "%(message)s"
logging.basicConfig(
    level="WARN", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("fred")


# TODO use this
class PromptTemplateArgs(BaseModel):
    human_input: str
    # factoids: str
    chat_history: Sequence[BaseMessage]


class DebugOptions(BaseModel):
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


class Fred:
    def __init__(
        self,
        ai_name: str = "Fred",
        human_name: str = "Human",
        ignore_home_assistant_ssl: str | bool | None = False,
        debug_options: DebugOptions = DebugOptions(),
    ):
        """
        _summary_

        Parameters
        ----------
        ai_name : str, optional
            Set your assistant's name, by default "Fred"
        human_name : str, optional
            Your name, or how you'd like to be addressed by the assistant. The assistant
            might search for Home Assistant entities using your name. e.g., if you ask
            "turn my lights off," it may decide to search for "turn off <your name>
            light," so you may get better results by using your name if your devices
            include your name. 'Human' by default.
        debug_options : DebugOptions, optional
            Configure `log_level`, `is_dry_run`, and `should_save_requests`.
        dry_run : bool, optional

        ignore_home_assistant_ssl : str | bool | None, optional
            If falsy, will not verify Home Assistant's SSL certificate. By default, False
        """
        self.debug_options = debug_options
        self._setup_development_tools()

        self.ai_name = ai_name
        self.human_name = human_name
        # self.factoids_vector_store = VectorStore("factoids")
        # one vector store for past conversations
        # one vector store for factoids/conclusions about the master
        # one vector store for tools (APIs)
        self.home_assistant_tool_store = HomeAssistantToolStore(
            base_url=os.environ["FRED_HA_BASE_URL"],
            dry_run=self.debug_options.is_dry_run,
            verify_home_assistant_ssl=not ignore_home_assistant_ssl,
        )

        log.info("Creating chat_history...")
        self.chat_history = ChatMessageHistory()
        log.info("Creating prompt_template...")
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=f"You are a personal assistant for {self.human_name}. "
                    f"Your name is {self.ai_name}."
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
        self.llm = ChatOpenAI(
            # model=OpenAIModel.GPT_4_0613,
            model=OpenAIModel.GPT_3_5_TURBO_0613,  # this mostly works, but sometimes is a little stupid
            api_key=SecretStr(os.environ["FRED_OPENAI_API_KEY"]),
            temperature=0,
        )

        # this order is important; the agent and agent executor will need to be able to
        # get tools added to them during an `invoke`, and to do that I need references
        # to the agent and agent executor. so I create a placeholder for tools, create
        # the agent and the executor, and then add at least one tool to them before
        # invoking anything.
        self.tools: list[BaseTool] = []
        log.info("Creating agent...")
        agent = MutableToolsOpenAiToolsAgent(
            runnable=create_openai_tools_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=self.prompt_template,
            )
        )
        log.info("Creating agent_executor...")
        self.agent_executor = MutableToolsAgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=self._is_verbose(),
        )
        self.tools.append(
            self.home_assistant_tool_store.get_tool_searcher_tool(self.agent_executor)
        )
        log.info("Adding tools to the agent executor...")
        self.agent_executor.add_tools(self.tools)

        self.timestamp_to_prompts_sent: dict[str, dict[str, Any]] = {}

        log.info("Fred is initialized.")

    def _is_verbose(self) -> bool:
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
        if self.debug_options.is_dry_run and not self._is_verbose():
            print(
                f"Bypassing logger to warn you that you probably want dry_run=True and log_level='info'. You have {self.debug_options.is_dry_run=} and {self.debug_options.log_level=}"
            )

    # def _get_k_relevant_factoids(self, human_input: str, k: int = 5) -> SystemMessage:
    #     factoids = self.factoids_vector_store.get_top_k_relevant_items_in_db(
    #         human_input, k
    #     )
    #     temp = ""
    #     for factoid in factoids.relevant_items_and_scores:
    #         temp += f" - {factoid.item.item_str}\n"
    #     return SystemMessage(
    #         content=f"Here are some facts that may or may not be relevant to the query:\n{temp}"
    #     )

    def ask_fred(self, human_input: str) -> str:  # TODO type this better
        k = 6
        relevant_wrapped_tools = (
            self.home_assistant_tool_store.get_k_relevant_home_assistant_tools(
                f"{self.human_name} {human_input}", k=k
            )
        )
        potentially_relevant_tools = [
            relevant_wrapped_tool.hass_tool
            for relevant_wrapped_tool in relevant_wrapped_tools
        ]
        log.info(
            f"Retrieved {len(potentially_relevant_tools)} tools: {[potentially_relevant_tool.name for potentially_relevant_tool in potentially_relevant_tools]}"
        )
        self.agent_executor.add_tools(potentially_relevant_tools)
        try:
            with save_chat_create_inputs_as_dict(
                self.llm.client, self.timestamp_to_prompts_sent
            ):
                response = self.agent_executor.invoke(
                    {
                        "human_input": human_input,
                        "chat_history": self.chat_history.messages,
                        # "factoids": self._get_k_relevant_factoids(human_input, k=5),
                    }
                )
        except openai.RateLimitError:
            log.exception(
                "OpenAI rate-limited you or you have an OpenAI quota problem. Check your token's usage at https://platform.openai.com/usage."
            )
            response = {"output": "Failed due to an API error. Should I retry?"}
        except Exception as e:
            response = {"output": "Failed due to an unforeseen issue."}
            raise e

        self.chat_history.add_user_message(
            HumanMessage(name=self.human_name, content=human_input)
        )
        self.chat_history.add_ai_message(
            AIMessage(name=self.ai_name, content=response["output"])
        )

        # TODO be smarter about resetting tools
        self.agent_executor.reset_tools(self.tools)

        return str(response["output"])

    def _write_requests_to_disk(self) -> None:
        with open(self.debug_options.requests_filename, "w") as requests_file:
            json.dump(self.timestamp_to_prompts_sent, requests_file, indent=4)

    def _shutdown(self) -> Never:
        log.info("Shutting down gracefully.")
        # self.factoids_vector_store.save_db_to_disk()
        if self.debug_options.should_save_requests:
            self._write_requests_to_disk()
        rich_print(f"\n'{self.ai_name}': Goodbye.")
        sys.exit(0)

    def start(self) -> Never:
        """
        Starts a chat interface in your terminal. Consumes the terminal.
        """
        rich_print("Type '/quit' to quit and '/help' for all options.")

        ai_intro_message = f"'{self.ai_name}': What can I do for you?"
        rich_print(f"\n{ai_intro_message}")
        self.chat_history.add_ai_message(
            AIMessage(name=self.ai_name, content=ai_intro_message)
        )

        while True:
            human_input = input(f"\n{self.human_name}: ")

            if human_input.lower() in ["/quit", "/exit"]:
                self._shutdown()
            elif human_input.lower() in ["/help"]:
                rich_print("'/quit' to quit")
            else:
                rich_print(f"\n'{self.ai_name}': {self.ask_fred(human_input)}")
