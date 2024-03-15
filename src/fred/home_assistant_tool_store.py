import json
import logging
import os
from homeassistant_api import Client, Domain, Group, Service, Entity
from urllib.parse import urljoin
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel as BaseModelV1
from pydantic import RootModel
from fred.errors import FredError
from fred.vector_store import VectorStore, VectorStoreItem

log = logging.getLogger("fred")

SUPPORTED_DOMAINS = set(["switch", "media_player"])


class SerializableHomeAssistantToolWrapper(BaseModelV1):
    domain_id: str
    service_id: str
    entity_id: str
    name: str
    description: str
    hass_service_entity_tool: BaseTool


class Domains(RootModel):  # type: ignore[type-arg]
    root: dict[str, Domain]


class HomeAssistantToolStore:
    def __init__(self, base_url: str, hass_token: str = "", dry_run: bool = False):
        api_url = urljoin(base_url, "/api")
        hass_token = self._get_hass_token(hass_token)
        self.dry_run = dry_run

        # TODO pick one of "home_assistant", "hass", "ha". I keep switching
        self.hass_client = Client(
            api_url=api_url,
            token=hass_token,
        )

        self.vector_store = VectorStore("hass_tools")
        self.domains: dict[str, Domain] = {}
        self.entities: dict[str, Group] = {}
        self.wrapped_tools: dict[str, SerializableHomeAssistantToolWrapper] = {}

        self.domains = self._get_domains()
        self.entities = self._get_entities()
        self.wrapped_tools = self._get_wrapped_tools()

        vector_store_tools: list[VectorStoreItem] = [
            VectorStoreItem(
                item_str=tool.description,
                # this bullshit below is necessary because langchain only supports
                # pydantic v1, and pydantic does not support a v2 BaseModel
                # (SerializableHomeAssistantToolWrapper) working with a v1 BaseModel
                # (tool.hass_service_entity_tool). But a v2 BaseModel can do
                # `.model_dump(exclude={"hass_service_entity_tool"})`, which is
                # useful here because that field can't be serialized
                #
                # i.e., if langchain were on pydantic v2, we could instead do:
                # `metadata=tool.model_dump(exclude={"hass_service_entity_tool"})`
                metadata={
                    "domain_id": tool.domain_id,
                    "service_id": tool.service_id,
                    "entity_id": tool.entity_id,
                    "name": tool.name,
                    "description": tool.description,
                },
                # tool.model_dump(exclude={"hass_service_entity_tool"}),
            )
            for tool in self.wrapped_tools.values()
        ]
        self.vector_store.generate_embeddings_and_save_embeddings_to_db(
            vector_store_tools
        )

    def _get_hass_service_entity_tool_instantiator_func(
        self, domain: Domain, service: Service, entity: Entity, dry_run: bool = False
    ) -> type[BaseTool]:
        entity_friendly_name = entity_friendly_name = (
            entity.state.attributes.get("friendly_name") or entity.slug
        )

        class HassServiceEntityToolArgs(BaseModelV1):
            pass

        class HassServiceEntityTool(BaseTool):
            name: str = f"{service.service_id}_{entity.entity_id.replace('.', '_')}"  # OpenAI doesn't like periods in tool (function) names
            description: str = f'For {entity_friendly_name}: {service.description or "[description not found]"}'
            return_direct: bool = True
            args_schema: type[BaseModelV1] = HassServiceEntityToolArgs

            def get_description_for_vector_store(self) -> str:
                return self.description

            def _run(_s) -> str:
                if not dry_run:
                    self.hass_client.trigger_service(
                        domain=domain.domain_id,
                        service=service.service_id,
                        entity_id=entity.entity_id,
                    )
                else:
                    log.info(
                        f"Dry run: would have called {domain.domain_id}.{service.service_id} on {entity.entity_id}"
                    )
                return f"Successfully called {domain.domain_id}.{service.service_id} on {entity_friendly_name}"

        return HassServiceEntityTool

    def _get_hass_token(self, hass_token: str) -> str:
        if hass_token == "":
            hass_environment_variable_value = os.environ.get("FRED_HA_TOKEN")
            if not hass_environment_variable_value:
                raise FredError(
                    "No Home Assistant API token was provided and there is no environment variable. Please provide one or set the environment variable `FRED_HA_TOKEN`."
                )
            else:
                hass_token = hass_environment_variable_value
        return hass_token

    def get_k_relevant_home_assistant_tools(
        self, human_input: str, k: int = 5
    ) -> list[BaseTool]:
        relevant_tools_search_results = (
            self.vector_store.get_top_k_relevant_items_in_db(
                human_input, k
            ).relevant_items_and_scores
        )
        return [
            self._tool_search_result_to_unwrapped_tool(tool_search_result.item)
            for tool_search_result in relevant_tools_search_results
        ]

    def _tool_search_result_to_unwrapped_tool(
        self, tool_search_result: VectorStoreItem
    ) -> BaseTool:
        return self.wrapped_tools[
            tool_search_result.metadata["name"]
        ].hass_service_entity_tool

    def _get_domains(self) -> dict[str, Domain]:
        if self.domains:
            return self.domains

        domains_filename = "hass_domains.json"
        if os.path.exists(domains_filename):
            log.info(f"Loading the existing hass domains from {domains_filename}.")
            # with open(domains_filename, "r") as domains_file:
            #     self.domains = Domains.model_validate(
            #         json.load(domains_file),
            #         strict=False,
            #         # strict is necessary because a domain has a service which has a
            #         # domain (cycle)
            #     ).root
        else:
            log.info(
                f"No existing {domains_filename} found. Hitting the Home Assistant API for domains."
            )
            self.domains = self.hass_client.get_domains()
            log.info(f"Saving domains to {domains_filename}.")
            # with open(domains_filename, "w") as domains_file:
            #     json_serializable_domains = {
            #         domain_key: domain.model_dump()
            #         for domain_key, domain in self.domains.items()
            #     }
            #     json.dump(json_serializable_domains, domains_file, indent=4)
        return self.domains

    def _get_entities(self) -> dict[str, Group]:
        if self.entities:
            return self.entities

        entities_filename = "hass_entities.json"
        if os.path.exists(entities_filename):
            log.info(f"Loading the existing hass entities from {entities_filename}.")
            with open(entities_filename, "r") as entities_file:
                self.entities = json.load(entities_file)  # this needs fixing
        else:
            log.info(
                f"No existing {entities_filename} found. Hitting the Home Assistant API for entities."
            )
            self.entities = self.hass_client.get_entities()
            log.info(f"Saving entities to {entities_filename}.")
            # with open(entities_filename, "w") as entities_file:
            #     json_serializable_entities = {
            #         group_key: group.model_dump()
            #         for group_key, group in self.entities.items()
            #     }
            #     json.dump(
            #         json_serializable_entities,
            #         entities_file,
            #         indent=4,
            #         default=str,  # prob not good because datetimes don't get (de)serialized?
            #     )
        return self.entities

    def _get_wrapped_tools(self) -> dict[str, SerializableHomeAssistantToolWrapper]:
        self.wrapped_tools = self.wrapped_tools or self._create_wrapped_tools()
        return self.wrapped_tools

    def _create_wrapped_tools(self) -> dict[str, SerializableHomeAssistantToolWrapper]:
        wrapped_tools: dict[str, SerializableHomeAssistantToolWrapper] = {}
        domains = self._get_domains()
        entities = self._get_entities()

        for domain_id, domain in domains.items():
            if domain_id in SUPPORTED_DOMAINS:
                for entity_slug, entity in entities[domain_id].entities.items():
                    # if "utkashs_bedroom_ceiling" in entity_slug:
                    for _, service in domain.services.items():
                        if service.fields:
                            log.info(
                                f"Skipping creating tool for {service.service_id}_{entity.entity_id.replace('.', '_')}."
                            )
                        else:
                            get_hass_service_entity_tool = (
                                self._get_hass_service_entity_tool_instantiator_func(
                                    domain, service, entity, dry_run=self.dry_run
                                )
                            )
                            tool: BaseTool = get_hass_service_entity_tool(
                                name=f"{service.service_id}_{entity.entity_id.replace('.', '_')}",
                                description=f'For {entity.state.attributes.get("friendly_name") or entity_slug}: {service.description or "[description not found]"}',
                            )
                            log.info(f"{tool.description=}")
                            wrapped_tools[tool.name] = (
                                SerializableHomeAssistantToolWrapper(
                                    domain_id=domain.domain_id,
                                    service_id=service.service_id,
                                    entity_id=entity.entity_id,
                                    name=tool.name,
                                    description=tool.description,
                                    hass_service_entity_tool=tool,
                                )
                            )
                            log.info(f"Created tool {tool.name}.")

        return wrapped_tools
