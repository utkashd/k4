import os
from typing import Any
from transformers import AutoTokenizer, AutoModel, PreTrainedModel
import torch
from pydantic import BaseModel, RootModel
import json
import logging

log = logging.getLogger("fred")


class VectorStoreItem(BaseModel):
    item_str: str
    metadata: Any = None


class VectorStoreItems(RootModel):  # type: ignore[type-arg]
    root: list[VectorStoreItem]


class RelevanceSearchSingleResult(BaseModel):
    item: VectorStoreItem
    relevance: float
    "TODO: description for relevance"


class RelevanceSearchResult(BaseModel):
    query_item: VectorStoreItem
    relevant_items_and_scores: list[RelevanceSearchSingleResult]


class VectorStore:
    def __init__(
        self,
        name: str,
    ):
        # TODO validate the name (ensure it can be a filename, etc)
        self.name = name
        self._has_db_changed_since_last_save = False

        log.info(f"Initializing {self}...")
        log.info("Loading the model from HuggingFace Hub...")
        self.model: PreTrainedModel = AutoModel.from_pretrained(
            "BAAI/bge-small-en-v1.5"
        )
        # prevent training behavior, e.g., stochastic dropout. Ensures that inferencing
        # is consistent
        self.model.eval()

        self.tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")

        self.items_filename = f"{name}_vector_store_items.json"
        self.items: list[VectorStoreItem] = self._get_vector_store_items_from_file(
            self.items_filename
        )

        self.embeddings_filename = f"{name}_vector_store_embeddings.pt"
        self.embeddings = self._get_vector_store_embeddings_from_file(
            self.embeddings_filename
        )

        log.info("Vector store initialized.")

    def _get_vector_store_items_from_file(
        self, items_filename: str
    ) -> list[VectorStoreItem]:
        log.info(f"Loading any existing items from {items_filename}...")
        if os.path.exists(items_filename):
            with open(items_filename, "r") as items_file:
                return VectorStoreItems(json.load(items_file)).root
        else:
            return []

    def _get_vector_store_embeddings_from_file(
        self, embeddings_filename: str
    ) -> torch.Tensor:
        log.info(f"Loading any existing embedding data from {embeddings_filename}...")
        if os.path.exists(embeddings_filename):
            log.info("Existing embedding data found.")
            embeddings: torch.Tensor = torch.load(embeddings_filename)
            return embeddings
        else:
            log.info("No existing embedding data found; the file doesn't exist.")
            return torch.Tensor()

    def __str__(self) -> str:
        return f"VectorStore(name={self.name},id={id(self)})"

    def save_db_to_disk(self) -> None:
        if self._has_db_changed_since_last_save:
            log.info(f"Saving {self} to disk...")
            with open(self.items_filename, "w") as items_file:
                json_serializable_items = [item.model_dump() for item in self.items]
                json.dump(json_serializable_items, items_file, indent=4)
            torch.save(self.embeddings, self.embeddings_filename)
            self._has_db_changed_since_last_save = False
        else:
            log.info(
                f"Skipping saving {self} to disk, because there are no changes to save."
            )

    def _generate_embeddings(self, items: list[VectorStoreItem]) -> torch.Tensor:
        # Tokenize items
        encoded_input = self.tokenizer(
            [item.item_str for item in items],
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
            item_embeddings: torch.Tensor = model_output[0][:, 0]
        # normalize embeddings
        normalized_embeddings = torch.nn.functional.normalize(
            item_embeddings, p=2, dim=1
        )
        return normalized_embeddings

    def generate_embeddings_and_save_embeddings_to_db(
        self, items: list[VectorStoreItem]
    ) -> torch.Tensor:
        self.items.extend(items)
        embeddings = self._generate_embeddings(items)
        self.embeddings = torch.concatenate((self.embeddings, embeddings))
        self._has_db_changed_since_last_save = True
        return embeddings

    def _compute_relevance_scores_against_db(
        self,
        item: VectorStoreItem,
    ) -> torch.Tensor:
        embedding = self._generate_embeddings([item])
        relevance_scores = (embedding @ self.embeddings.T)[0]
        return relevance_scores

    def get_top_k_relevant_items_in_db(
        self, item_or_query: VectorStoreItem | str, k: int
    ) -> RelevanceSearchResult:
        item: VectorStoreItem = (
            item_or_query
            if isinstance(item_or_query, VectorStoreItem)
            else VectorStoreItem(item_str=item_or_query)
        )
        if k > len(self.items):
            log.info(
                f"Too few items in {self} to perform a meaningful relevance search."
            )
            k = len(self.items)
        relevance_scores = self._compute_relevance_scores_against_db(item)
        most_relevant_strings = torch.topk(
            relevance_scores, k=min(k, len(self.items)), sorted=True, largest=True
        )
        return RelevanceSearchResult(
            query_item=item,
            relevant_items_and_scores=[
                RelevanceSearchSingleResult(
                    item=self.items[most_relevant_strings.indices[idx]],
                    relevance=float(most_relevant_strings.values[idx].item()),
                )
                for idx in range(k)
            ],
        )
