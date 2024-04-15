from functools import cached_property
import json
import sys
import os
import logging
from typing import Any, Literal, Never, Sequence
import openai
from pydantic import BaseModel

from gpt_home.vector_store import VectorStore, VectorStoreItem, VectorStoreItemNotInDb
from gpt_home.home_assistant_tool_store import HomeAssistantToolStore
from gpt_home.mutable_tools_agent_executor import MutableToolsAgentExecutor
from gpt_home.mutable_tools_openai_tools_agent import MutableToolsOpenAiToolsAgent
from gpt_home.openai_model import OpenAIModel
from gpt_home.utils.save_llm_prompt import save_chat_create_inputs_as_dict
from langchain_core.pydantic_v1 import SecretStr
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import (
    PromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.runnables import RunnableSerializable
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent
from langchain.tools import BaseTool
from rich.logging import RichHandler
from rich import print as rich_print


FORMAT = "%(message)s"
logging.basicConfig(
    level="WARN", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("gpt_home")


# TODO use this
class PromptTemplateArgs(BaseModel):
    human_input: str
    # factoids: str
    chat_history: Sequence[BaseMessage]


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


class GptHome:
    def __init__(
        self,
        ai_name: str = "GptHome",
        human_name: str = "Human",
        ignore_home_assistant_ssl: str | bool = False,
        debug_options: GptHomeDebugOptions = GptHomeDebugOptions(),
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
        self.ai_name = ai_name
        self.human_name = human_name
        self.home_assistant_tool_store = HomeAssistantToolStore(
            base_url=os.environ["GPT_HOME_HA_BASE_URL"],
            dry_run=self.debug_options.is_dry_run,
            verify_home_assistant_ssl=not ignore_home_assistant_ssl,
        )
        log.info("Creating chat_history...")
        self.chat_history = ChatMessageHistory()
        log.info("Creating prompt_template...")
        self.tool_calling_prompt_template = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=f"You are a personal AI assistant for {self.human_name}. "
                    f"Your name is {self.ai_name}. When opportune, ask simple questions "
                    f"to learn more about {self.human_name}'s preferences."
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

        # Set up instance variables for managing and using factoids.
        self.factoids_vector_store = VectorStore("factoids")
        # one vector store for past conversations
        # one vector store for factoids/conclusions about the master
        # one vector store for tools (APIs)

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
                f"Bypassing logger to warn you that you probably want dry_run=True and log_level='info'. You have {self.debug_options.is_dry_run=} and {self.debug_options.log_level=}"
            )

    def _get_k_relevant_factoids(self, human_input: str, k: int = 5) -> SystemMessage:
        factoids = self.factoids_vector_store.get_top_k_relevant_items_in_db(
            human_input, k
        )
        if len(factoids.relevant_items_and_scores) == 0:
            return SystemMessage(content="")
        temp = ""
        for factoid in factoids.relevant_items_and_scores:
            temp += f" - {factoid.item.item_str}\n"
        return SystemMessage(
            content=f"Here are some facts that may or may not be relevant to the query:\n{temp}"
        )

    @cached_property
    def factoids_chain(self) -> RunnableSerializable[dict[Any, Any], Any]:
        factoids_llm = ChatOpenAI(
            model=OpenAIModel.GPT_4_TURBO_PREVIEW,
            api_key=SecretStr(os.environ["GPT_HOME_OPENAI_API_KEY"]),
            temperature=0,
        )
        factoids_prompt_template = PromptTemplate.from_template(
            template_format="f-string",
            template=f"Review the following chat history between a human ({self.human_name}) "
            f"and an AI assistant ({self.ai_name}). Your task is to draw succinct conclusions "
            "about the human that may be relevant to future conversations between the human and "
            "the AI assistant, e.g., personal preferences, facts relevant to controlling devices. "
            'If nothing useful can be concluded, respond "<no conclusions>". Have a bias for not '
            "drawing any conclusions."
            "\n"
            "\nExample:"
            f"\n{self.ai_name}: What can I do for you?"
            f"\n{self.human_name}: turn on tv and turn lights off"
            f"\n{self.ai_name}: I have turned on your television and I have turned your "
            "bedroom light off. Is there anything else I can help you with?"
            f"\n{self.human_name}: set thermostat to heat 66 degrees\n"
            f"\n{self.ai_name}: Ok, I have turned on the Bedroom's thermostat and set it "
            "to heat at 66 degrees Fahrenheit. Do you usually want this when you watch TV?"
            f"\n{self.human_name}: no\n"
            "\n\nConclusions:"
            f"\n{self.human_name} may prefer the lights to be off when they watch TV."
            f"\n{self.human_name}'s preferred thermostat heating temperature may be 66 degrees F."
            "\n"
            "\nExample:"
            f"\n{self.ai_name}: What can I do for you?"
            f"\n{self.human_name}: turn my light on pls"
            f"\n{self.ai_name}: I have turned on your light. Is there anything else I can help you with?"
            "\n\nConclusions:"
            f"\n<no conclusions>"
            "\n"
            "\nChat History:"
            "\n{chat_history}"
            "\n\nConclusions:"
            "\n",
        )

        return factoids_prompt_template | factoids_llm

    @cached_property
    def factoids_check_duplicates_chain(
        self,
    ) -> RunnableSerializable[dict[Any, Any], Any]:
        factoids_check_duplicates_llm = ChatOpenAI(
            model=OpenAIModel.GPT_4_TURBO_PREVIEW,
            api_key=SecretStr(os.environ["GPT_HOME_OPENAI_API_KEY"]),
            temperature=0,
        )
        factoids_check_duplicates_prompt_template = PromptTemplate.from_template(
            template_format="f-string",
            template="The following 4 statements reflect what we currently know:"
            "\n{four_existing_factoids_numbered}"
            "\n\nWe've received 1 new statement: {new_factoid}"
            "\n\nWe need to store as few statements as possible while keeping all information. "
            "Which of the following actions should we perform? Indicate all that apply. "
            "Only include the letter(s). Do not provide an explanation or any other information."
            "\nA. Keep all 5 statements."
            "\nB. Overwrite the 1st statement with the new statement"
            "\nC. Overwrite the 2nd statement with the new statement"
            "\nD. Overwrite the 3rd statement with the new statement"
            "\nE. Overwrite the 4th statement with the new statement"
            "\nF. Discard the new statement, because it doesn't contain new information."
            "\n\nAnswer: ",
        )

        return factoids_check_duplicates_prompt_template | factoids_check_duplicates_llm

    # TODO i should classify all factoids as "always supply to llm" or "require querying"
    def _learn_about_human(self) -> None:
        """
        Feeds the chat history plus a "what conclusions can you draw from this chat"
        prompt to an LLM to get a list of factoids. Then, adds the factoids to the
        factoids db
        """

        if len(self.chat_history.messages) == 0:
            # we have no chat history to use, don't try to "learn" anything
            return

        def get_factoids_to_overwrite(
            factoid: str,
        ) -> set[VectorStoreItem] | Literal["discard"]:
            """
            Returns 'discard' to indicate that the factoid should just be discarded.
            Otherwise, returns a set for which factoids should be removed in favor of
            this new factoid.
            """
            if self.factoids_vector_store.is_empty():
                return set()

            similar_factoids = (
                self.factoids_vector_store.get_top_k_relevant_items_in_db(factoid, k=4)
            )
            existing_factoids_numbered = ""
            for index, similar_factoid in enumerate(
                similar_factoids.relevant_items_and_scores
            ):
                existing_factoids_numbered += (
                    f"{index + 1}. {similar_factoid.item.item_str}"
                )
                if index < 3:
                    existing_factoids_numbered += "\n"
            if len(similar_factoids.relevant_items_and_scores) < 4:
                # this means that the factoids db had fewer than 4 factoids
                # we're just gonna add bogus factoids for filler. yikes!
                # should probably fix this...but for now...this will work
                factoids_to_add = 4 - len(similar_factoids.relevant_items_and_scores)
                match factoids_to_add:
                    case 3:
                        extra_factoids = (
                            "2. Mowgli is a character in The Jungle Book.\n"
                            "3. Bagheera is a character in The Jungle Book.\n"
                            "4. Baloo is a character in The Jungle Book."
                        )
                    case 2:
                        extra_factoids = (
                            "3. Bagheera is a character in The Jungle Book.\n"
                            "4. Baloo is a character in The Jungle Book."
                        )
                    case 1:
                        extra_factoids = "4. Baloo is a character in The Jungle Book."
                    case _:
                        extra_factoids = ""

                existing_factoids_numbered += extra_factoids

            response = self.factoids_check_duplicates_chain.invoke(
                {
                    "four_existing_factoids_numbered": existing_factoids_numbered,
                    "new_factoid": factoid,
                }
            )
            assert isinstance(response, AIMessage)
            assert isinstance(response.content, str)
            factoids_to_overwrite: set[VectorStoreItem] = set()
            if "A" in response.content:
                return set()
            if "F" in response.content:
                return "discard"
            if "B" in response.content:
                factoids_to_overwrite.add(
                    similar_factoids.relevant_items_and_scores[0].item
                )
            if "C" in response.content:
                if len(similar_factoids) >= 2:
                    factoids_to_overwrite.add(
                        similar_factoids.relevant_items_and_scores[1].item
                    )
            if "D" in response.content:
                if len(similar_factoids) >= 3:
                    factoids_to_overwrite.add(
                        similar_factoids.relevant_items_and_scores[2].item
                    )
            if "E" in response.content:
                if len(similar_factoids) >= 4:
                    factoids_to_overwrite.add(
                        similar_factoids.relevant_items_and_scores[3].item
                    )

            return factoids_to_overwrite

        # TODO somehow ensure I don't add something that is already in the db
        formatted_chat_history = "\n".join(
            [f"{msg.name}: {msg.content}" for msg in self.chat_history.messages]
        )
        response = self.factoids_chain.invoke({"chat_history": formatted_chat_history})
        assert isinstance(response, AIMessage)
        assert isinstance(response.content, str)
        if "<no conclusion>" in response.content:
            rich_print(f"no conclusions: {response=}")
        else:
            factoid_items: list[VectorStoreItemNotInDb] = []
            factoids_to_remove: list[VectorStoreItem] = []
            for new_factoid_str in response.content.split("\n"):
                # we're assuming that the factoids don't have any duplicates among them
                factoids_to_overwrite = get_factoids_to_overwrite(new_factoid_str)
                if factoids_to_overwrite == "discard":
                    # this means that our "new factoid" isn't actually new information.
                    # so we're are not adding this to our factoids db
                    pass
                else:
                    for factoid_to_overwrite in factoids_to_overwrite:
                        factoids_to_remove.append(factoid_to_overwrite)
                    factoid_items.append(
                        VectorStoreItemNotInDb(item_str=new_factoid_str)
                    )
            self.factoids_vector_store.remove_items(factoids_to_remove)
            self.factoids_vector_store.generate_embeddings_and_save_embeddings_to_db(
                factoid_items
            )

    def _intro(self) -> None: ...

    def _clear_factoids(self) -> None:
        self.factoids_vector_store.clear_db()

    def ask_gpt_home(self, human_input: str) -> list[str]:  # TODO type this better
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
        rich_print(
            f"[italic blue]Preemptively retrieved {len(potentially_relevant_tools)} tools: {[potentially_relevant_tool.name for potentially_relevant_tool in potentially_relevant_tools]}[/italic blue]"
        )
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
                        "chat_history": self.chat_history.messages,
                        "factoids": self._get_k_relevant_factoids(human_input, k=5),
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

        return [str(response["output"])]

    def _write_requests_to_disk(self) -> None:
        with open(self.debug_options.requests_filename, "w") as requests_file:
            json.dump(self.timestamp_to_prompts_sent, requests_file, indent=4)

    def _save_self_to_disk(self) -> None:
        self.factoids_vector_store.save_db_to_disk()
        if self.debug_options.should_save_requests:
            self._write_requests_to_disk()

    def _shutdown(self) -> Never:
        log.info("Shutting down gracefully.")
        self._save_self_to_disk()
        rich_print(f"\n'{self.ai_name}': Goodbye.")
        sys.exit(0)

    def stop_chatting(self) -> None:
        self._learn_about_human()
        self._save_self_to_disk()
        self.chat_history.clear()

    def start(self) -> Never:
        """
        Starts a chat interface in your terminal. Consumes the terminal. Used for
        debugging, so far.
        """

        import readline  # this improves the terminal UI--input() now ignores arrow keys  # noqa: F401

        rich_print("Type '/quit' to quit and '/help' for all options.")

        ai_intro_message = "What can I do for you?"
        rich_print(f"\n'{self.ai_name}': {ai_intro_message}")
        self.chat_history.add_ai_message(
            AIMessage(name=self.ai_name, content=ai_intro_message)
        )

        while True:
            human_input = input(f"\n{self.human_name}: ")

            if human_input.lower() in ["/quit", "/exit", "quit"]:
                self._shutdown()
            elif human_input.lower() in ["/help"]:
                rich_print("'/quit' to quit")  # the rest is just for developing
            elif human_input.lower() in ["/clear_chat"]:
                self.chat_history.clear()
                rich_print("Chat history cleared.")
            elif human_input.lower() in ["/clear_factoids"]:
                self._clear_factoids()
                rich_print("All factoids deleted.")
            elif human_input.lower() in ["/clear"]:
                self.chat_history.clear()
                rich_print("Chat history cleared.")
                self._clear_factoids()
                rich_print("All factoids deleted.")
            elif human_input.lower() in ["/glean"]:
                self._learn_about_human()
                self._save_self_to_disk()
            else:
                gpt_home_responses = self.ask_gpt_home(human_input)
                for msg in gpt_home_responses:
                    rich_print(f"\n'{self.ai_name}': {msg}")
