import sys
import os
import logging
from typing import Never, Sequence
from pydantic import BaseModel
from fred.home_assistant_tool_store import HomeAssistantToolStore
from fred.vector_store import VectorStore
from langchain_core.pydantic_v1 import SecretStr
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ChatMessageHistory
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.agents.agent import RunnableAgent
from fred.openai_model import OpenAIModel
from rich.logging import RichHandler
from rich import print as rich_print

# import langchain

# langchain.debug = True


FORMAT = "%(message)s"
logging.basicConfig(
    level="WARN", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)
log = logging.getLogger("fred")


# TODO use this
class PromptTemplateArgs(BaseModel):
    human_input: str
    factoids: str
    chat_history: Sequence[BaseMessage]


class Fred:
    def __init__(
        self,
        log_level: str = "warn",
        ai_name: str = "Fred",
        human_name: str = "Human",
    ):
        if os.environ.get("TOKENIZERS_PARALLELISM") != "true":
            # if the user hasn't set this environment variable, don't overwrite it.
            # otherwise (in here), set it to false to avoid a warning from huggingface
            # https://stackoverflow.com/questions/62691279/how-to-disable-tokenizers-parallelism-true-false-warning
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
        self.verbose = log_level.lower() in ["debug", "info"]
        # we have to do this now to avoid some unwanted logging
        logging.basicConfig(
            level=log_level.upper(),
            format=FORMAT,
            datefmt="[%X]",
            handlers=[RichHandler()],
            force=True,
        )
        self.ai_name = ai_name
        self.human_name = human_name
        self.factoids_vector_store = VectorStore("factoids")
        # one vector store for past conversations
        # one vector store for factoids/conclusions about the master
        # one vector store for tools (APIs)
        self.home_assistant_tool_store = HomeAssistantToolStore(
            base_url=os.environ["FRED_HA_BASE_URL"]
        )

        self.llm = ChatOpenAI(
            model=OpenAIModel.GPT_4_0613,
            api_key=SecretStr(os.environ["FRED_OPENAI_API_KEY"]),
            temperature=0,
        )

        self.chat_history = ChatMessageHistory()
        self.prompt_template = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=f"You are a personal assistant for {self.human_name}. "
                    f"Your name is {self.ai_name}."
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                # HumanMessage(content="{human_input}"), # TODO understand why I can't
                # do this, which seems much safer than the actual solution (below)
                ("human", "{factoids}"),
                # message types: Use one of 'human', 'user', 'ai', 'assistant', or 'system'
                ("human", "{human_input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
                # this `agent_scratchpad` is REQUIRED for OpenAI function calling. TODO
                # ensure that agent_scratchpad isn't accidentally left out, because
                # langchain is so shit at writing statically-checkable code
            ]
        )

    def _get_k_relevant_factoids(self, human_input: str, k: int = 5) -> SystemMessage:
        factoids = self.factoids_vector_store.get_top_k_relevant_items_in_db(
            human_input, k
        )
        temp = ""
        for factoid in factoids.relevant_items_and_scores:
            temp += f" - {factoid.item.item_str}\n"
        return SystemMessage(
            content=f"Here are some facts that may or may not be relevant to the query:\n{temp}"
        )

    def _ask_fred(self, human_input: str) -> str:  # TODO type this better
        tools = self.home_assistant_tool_store.get_k_relevant_home_assistant_tools(
            human_input, k=5
        )
        agent = RunnableAgent(
            runnable=create_openai_tools_agent(
                llm=self.llm,
                tools=tools,
                prompt=self.prompt_template,
            )
        )
        self.agent_executor = AgentExecutor(
            agent=agent, tools=tools, verbose=self.verbose
        )

        response = self.agent_executor.invoke(
            {
                "human_input": human_input,
                "chat_history": self.chat_history.messages,
                "factoids": self._get_k_relevant_factoids(human_input, k=5),
            }
        )

        self.chat_history.add_user_message(
            HumanMessage(name=self.human_name, content=human_input)
        )
        self.chat_history.add_ai_message(
            AIMessage(name=self.ai_name, content=response["output"])
        )

        return str(response["output"])

    def _shutdown(self) -> Never:
        log.info("Shutting down gracefully.")
        self.factoids_vector_store.save_db_to_disk()
        rich_print(f"\n'{self.ai_name}': Goodbye.")
        sys.exit(0)

    def start(self) -> Never:
        rich_print("Type 'quit' to quit.")

        ai_intro_message = f"'{self.ai_name}': What can I do for you?"
        rich_print(f"\n{ai_intro_message}")
        self.chat_history.add_ai_message(
            AIMessage(name=self.ai_name, content=ai_intro_message)
        )

        while True:
            human_input = input(f"\n{self.human_name}: ")

            if human_input.lower() in ["quit", "shutdown", "exit"]:
                self._shutdown()

            rich_print(f"\n'{self.ai_name}': {self._ask_fred(human_input)}")
