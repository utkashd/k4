from functools import cached_property
from pathlib import Path
from typing import Any, Literal
from cyris.openai_model import OpenAIModel
from cyris.vector_store import VectorStore, VectorStoreItem, VectorStoreItemNotInDb
from rich import print as rich_print
from langchain_core.messages import SystemMessage, AIMessage
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
from langchain_core.runnables import RunnableSerializable
from langchain_core.prompts import (
    PromptTemplate,
)
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import SecretStr
import os


class FactoidsStore:
    def __init__(
        self, ai_name: str, human_name: str, directory_to_load_from_and_save_to: Path
    ):
        self.factoids_vector_store = VectorStore(
            directory_to_load_from_and_save_to=directory_to_load_from_and_save_to,
            name="factoids",
        )
        self.ai_name = ai_name
        self.human_name = human_name

    @cached_property
    def factoids_chain(self) -> RunnableSerializable[dict[Any, Any], Any]:
        factoids_llm = ChatOpenAI(
            model=OpenAIModel.GPT_4_TURBO_PREVIEW,
            api_key=SecretStr(os.environ["CYRIS_OPENAI_API_KEY"]),
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
            api_key=SecretStr(os.environ["CYRIS_OPENAI_API_KEY"]),
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

    def _clear_factoids(self) -> None:
        self.factoids_vector_store.clear_db()

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

    # TODO i should classify all factoids as "always supply to llm" or "require querying"
    def _learn_about_human(self, chat_history: ChatMessageHistory) -> None:
        """
        Feeds the chat history plus a "what conclusions can you draw from this chat"
        prompt to an LLM to get a list of factoids. Then, adds the factoids to the
        factoids db
        """

        if len(chat_history.messages) == 0:
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
            [f"{msg.name}: {msg.content}" for msg in chat_history.messages]
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
