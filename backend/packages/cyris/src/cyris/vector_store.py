import os
from pathlib import Path
from typing import Any
from transformers import AutoTokenizer, AutoModel, PreTrainedModel  # type: ignore[import-untyped]
import torch
from pydantic import BaseModel, RootModel
import json
import logging

log = logging.getLogger("cyris")


class VectorStoreItemNotInDb(BaseModel):
    item_str: str
    metadata: Any = None


class VectorStoreItem(VectorStoreItemNotInDb):
    id: int

    def __hash__(self) -> int:
        return hash(self.id)


class VectorStoreItems(RootModel):  # type: ignore[type-arg]
    root: list[VectorStoreItem]


class RelevanceSearchSingleResult(BaseModel):
    item: VectorStoreItem
    relevance: float
    "TODO: description for relevance"


class RelevanceSearchResult(BaseModel):
    query_item: VectorStoreItemNotInDb
    relevant_items_and_scores: list[RelevanceSearchSingleResult]

    def __len__(self) -> int:
        return len(self.relevant_items_and_scores)


class VectorStore:
    def __init__(
        self,
        name: str,
        directory_to_load_from_and_save_to: Path,
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

        self.items_filename = Path(
            os.path.join(
                directory_to_load_from_and_save_to, f"{name}_vector_store_items.json"
            )
        )
        self.items: list[VectorStoreItem] = self._get_vector_store_items_from_file(
            self.items_filename
        )

        self.embeddings_filename = Path(
            os.path.join(
                directory_to_load_from_and_save_to, f"{name}_vector_store_embeddings.pt"
            )
        )
        self.embeddings = self._get_vector_store_embeddings_from_file(
            self.embeddings_filename
        )

        log.info("Vector store initialized.")

    def __len__(self) -> int:
        return len(self.items)

    def is_empty(self) -> bool:
        return len(self) == 0

    def remove_items(self, vector_store_items_to_remove: list[VectorStoreItem]) -> None:
        # this method is pretty gross, but this is probably only going to be called for
        # vector stores that are quite small. So the inefficiency is pretty inconsequential

        if len(vector_store_items_to_remove) == 0:
            return None
        indexes_to_remove: set[int] = {
            vector_store_item.id for vector_store_item in vector_store_items_to_remove
        }
        # important to do the embeddings before the items, since I'm relying on the
        # length of self.items to store the "old length"
        indexes_to_keep = [i for i in range(len(self)) if i not in indexes_to_remove]
        self.embeddings = self.embeddings[indexes_to_keep]

        self.items = [item for item in self.items if item.id not in indexes_to_remove]
        for index, item in enumerate(self.items):
            item.id = index

        if len(self.items) != len(self.embeddings):
            breakpoint()

        self._has_db_changed_since_last_save = len(vector_store_items_to_remove) > 0

    def _get_vector_store_items_from_file(
        self, items_filename: Path
    ) -> list[VectorStoreItem]:
        log.info(f"Loading any existing items from {items_filename}...")
        if items_filename.exists():
            # TODO ensure we don't get conflicts with writing/reading at the same time.
            # need some sort of lock mechanism here (and ideally one that doesn't
            # require manual fixing if cyris is killed mid-write)
            with open(items_filename, "r") as items_file:
                return VectorStoreItems(json.load(items_file)).root
        else:
            return []

    def _get_vector_store_embeddings_from_file(
        self, embeddings_filename: Path
    ) -> torch.Tensor:
        log.info(f"Loading any existing embedding data from {embeddings_filename}...")
        if embeddings_filename.exists():
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

    def _generate_embeddings(
        self, items: list[VectorStoreItemNotInDb] | list[VectorStoreItem]
    ) -> torch.Tensor:
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
        self, items: list[VectorStoreItemNotInDb]
    ) -> torch.Tensor | None:
        if len(items) == 0:
            log.warn("Asked to generate embeddings for an empty list.")
            return None
        vector_store_items: list[VectorStoreItem] = []
        for index, item in enumerate(items):
            vector_store_items.append(
                VectorStoreItem(
                    item_str=item.item_str,
                    metadata=item.metadata,
                    id=len(self.items) + index,
                )
            )
        self.items.extend(vector_store_items)
        embeddings = self._generate_embeddings(vector_store_items)
        self.embeddings = torch.concatenate((self.embeddings, embeddings))
        self._has_db_changed_since_last_save = True
        return embeddings

    def clear_db(self) -> None:
        if len(self.items):
            log.warn(f"Deleting all items in {self}.")
            self._has_db_changed_since_last_save = True
            self.items.clear()
            self.embeddings = torch.Tensor()
        else:
            log.warn(
                f"{self} was instructed to delete all items, but there aren't any."
            )

    def _compute_relevance_scores_against_db(
        self,
        item: VectorStoreItemNotInDb,
    ) -> torch.Tensor:
        embedding = self._generate_embeddings([item])
        relevance_scores = (embedding @ self.embeddings.T)[0]
        return relevance_scores

    def get_top_k_relevant_items_in_db(
        self, item_or_query: VectorStoreItemNotInDb | str, k: int
    ) -> RelevanceSearchResult:
        item: VectorStoreItemNotInDb = (
            item_or_query
            if isinstance(item_or_query, VectorStoreItemNotInDb)
            else VectorStoreItemNotInDb(item_str=item_or_query)
        )
        if len(self.items) == 0:
            return RelevanceSearchResult(query_item=item, relevant_items_and_scores=[])
        if k > len(self.items):
            log.info(
                f"Too few items in {self} to perform a meaningful relevance search."
            )
            k = len(self.items)
        relevance_scores = self._compute_relevance_scores_against_db(item)
        most_relevant_strings = torch.topk(
            relevance_scores, k=k, sorted=True, largest=True
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
