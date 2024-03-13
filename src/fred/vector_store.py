import os
from transformers import AutoTokenizer, AutoModel, PreTrainedModel
import torch
from pydantic import BaseModel
import json
import logging

log = logging.getLogger("fred")


class RelevanceSearchSingleResult(BaseModel):
    string: str
    relevance: float
    "TODO: description for relevance"


class RelevanceSearchResult(BaseModel):
    query_string: str
    relevant_strings_and_scores: list[RelevanceSearchSingleResult]


class VectorStore:
    def __init__(
        self,
        name: str,
    ):
        # TODO validate the name (ensure it can be a filename, etc)
        self.name = name
        self._has_db_changed_since_saving_to_disk = False

        log.info(f"Initializing {self}...")
        log.info("Loading the model from HuggingFace Hub...")
        self.model: PreTrainedModel = AutoModel.from_pretrained(
            "BAAI/bge-small-en-v1.5"
        )
        # prevent training behavior, e.g., stochastic dropout. Ensures that inferencing
        # is consistent
        self.model.eval()

        self.tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")

        self.strings_filename = f"{name}_strings.json"
        log.info(f"Loading any existing strings from {self.strings_filename}...")
        if os.path.exists(self.strings_filename):
            with open(self.strings_filename, "r") as strings_file:
                self.strings: list[str] = json.load(strings_file)
        else:
            self.strings = []

        self.embeddings_filename = f"{name}_embeddings.pt"
        log.info(
            f"Loading any existing embedding data from {self.embeddings_filename}..."
        )
        if os.path.exists(self.embeddings_filename):
            self.embeddings: torch.Tensor = torch.load(self.embeddings_filename)
            if len(self.strings) != len(self.embeddings):
                # if I manually changed the strings for testing purposes, regenerate the
                # embeddings from scratch
                log.info(
                    f"Detected a difference in length between {self.strings_filename} "
                    f"and {self.embeddings_filename}. Recomputing the embeddings."
                )
                self.embeddings = self.generate_embeddings(self.strings)
                self.save_db_to_disk()
        else:
            self.embeddings = torch.Tensor()

        log.info("Vector store initialized.")

    def __str__(self) -> str:
        return f"VectorStore(name={self.name},id={id(self)})"

    def save_db_to_disk(self) -> None:
        if self._has_db_changed_since_saving_to_disk:
            log.info(f"Saving {self} to disk...")
            with open(self.strings_filename, "w") as strings_file:
                json.dump(self.strings, strings_file, indent=4)
            torch.save(self.embeddings, self.embeddings_filename)
            self._has_db_changed_since_saving_to_disk = False
        else:
            log.info(
                f"Skipping saving {self} to disk, because there are no changes to save."
            )

    def generate_embeddings(self, strings: list[str]) -> torch.Tensor:
        # Tokenize strings
        encoded_input = self.tokenizer(
            strings,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=512,
        )
        # for s2p(short query to long passage) retrieval task, add an instruction to
        # query (not add instruction for passages) encoded_input =
        # tokenizer([instruction + q for q in queries], padding=True, truncation=True,
        # return_tensors='pt')

        # Compute token embeddings
        with torch.no_grad():
            model_output = self.model(**encoded_input)
            # Perform pooling. In this case, cls pooling.
            string_embeddings: torch.Tensor = model_output[0][:, 0]
        # normalize embeddings
        normalized_embeddings = torch.nn.functional.normalize(
            string_embeddings, p=2, dim=1
        )
        return normalized_embeddings

    def generate_embeddings_and_save_embeddings_to_db(
        self, strings: list[str]
    ) -> torch.Tensor:
        embeddings = self.generate_embeddings(strings)
        self.embeddings = torch.concatenate((self.embeddings, embeddings))
        self._has_db_changed_since_saving_to_disk = True
        return embeddings

    def _compute_relevance_scores_against_db(
        self,
        string: str,
    ) -> torch.Tensor:
        embedding = self.generate_embeddings([string])
        relevance_scores = (embedding @ self.embeddings.T)[0]
        return relevance_scores

    def get_top_k_relevant_strings_in_db(
        self, string: str, k: int
    ) -> RelevanceSearchResult:
        assert k < len(self.strings)  # TODO better handling of this
        relevance_scores = self._compute_relevance_scores_against_db(string)
        most_relevant_strings = torch.topk(
            relevance_scores, k=min(k, len(self.strings)), sorted=True, largest=True
        )
        return RelevanceSearchResult(
            query_string=string,
            relevant_strings_and_scores=[
                RelevanceSearchSingleResult(
                    string=self.strings[most_relevant_strings.indices[idx]],
                    relevance=float(most_relevant_strings.values[idx].item()),
                )
                for idx in range(k)
            ],
        )


def test() -> None:
    vector_store = VectorStore("factoids")

    query_string = "utkash needs to workout. what could he do?"

    most_relevant_strings = vector_store.get_top_k_relevant_strings_in_db(
        query_string, 5
    )

    log.info(most_relevant_strings)


if __name__ == "__main__":
    test()
