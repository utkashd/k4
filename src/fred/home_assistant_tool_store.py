import json
import logging
import os
from typing import Optional
from homeassistant_api import Client, Domain, Group, Service, Entity
from urllib.parse import urljoin
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from pydantic import RootModel
from fred.errors import FredError
from fred.mutable_tools_agent_executor import MutableToolsAgentExecutor
from fred.vector_store import VectorStore, VectorStoreItem
from rich import print as rich_print

log = logging.getLogger("fred")

SUPPORTED_DOMAINS = set(
    [
        "switch",
        # "media_player",
    ]
)


class SerializableHomeAssistantToolWrapper(BaseModel):
    domain_id: str
    service_id: str
    entity_id: str
    name: str
    description: str
    hass_service_entity_tool: BaseTool


class Domains(RootModel):  # type: ignore[type-arg]
    root: dict[str, Domain]


class HomeAssistantToolStore:
    """
    On initialization, hits the Home Assistant API to get all entities and services and
    uses that information to create many tools for interacting with Home Assistant
    entities.

    Maintains a vector store of these tools and exposes methods to query for tools. Also
    provides a function that returns a tool to query for tools.
    """

    def __init__(
        self,
        base_url: str,
        hass_token: str = "",
        dry_run: bool = False,
        verify_home_assistant_ssl: bool = True,
    ):
        self.dry_run = dry_run

        # TODO pick one of "home_assistant", "hass", "ha". I keep switching
        self.hass_client = self._create_hass_client(
            base_url, hass_token, verify_home_assistant_ssl
        )

        self.domains: dict[str, Domain] = {}
        self.entities: dict[str, Group] = {}
        self.wrapped_tools: dict[str, SerializableHomeAssistantToolWrapper] = {}
        self.tool_searcher_tool: BaseTool | None = None

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
        self.vector_store = VectorStore("hass_tools")
        self.vector_store.generate_embeddings_and_save_embeddings_to_db(
            vector_store_tools
        )

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

    def get_tool_searcher_tool(
        self,
        agent_executor: MutableToolsAgentExecutor,
    ) -> BaseTool:
        if not self.tool_searcher_tool:
            self.tool_searcher_tool = self._create_tool_searcher_tool(agent_executor)
        return self.tool_searcher_tool

    def _create_tool_searcher_tool(
        self,
        agent_executor: MutableToolsAgentExecutor,
    ) -> BaseTool:
        class SearchHassToolsToolArgs(BaseModel):
            query: str = Field(description="The query string")
            k: Optional[int] = Field(
                default=5,
                description="The maximum number of tools to get back.",
            )

        class SearchHassToolsTool(BaseTool):
            name: str = "search_device_tools"
            description: str = "Use this to search for more tools if you're not provided an appropriate tool. If you don't get a good fit the first time, retry with a larger `k` or with a better query, such as by including more context."
            return_direct: bool = False
            args_schema: type[BaseModel] = SearchHassToolsToolArgs

            def _run(_s, query: str, k: int = 5) -> str:
                rich_print(
                    f"\n[italic blue]Searching for {k=} Home Assistant tools with {query=}.[/italic blue]"
                )
                tools = self.get_k_relevant_home_assistant_tools(query, k)
                agent_executor.add_tools(tools)
                return f"Retrieved {len(tools)} tools: {tools=}"

        self.tool_searcher_tool = SearchHassToolsTool()
        return self.tool_searcher_tool

    def _create_hass_client(
        self, base_url: str, hass_token: str, verify_home_assistant_ssl: bool = True
    ) -> Client:
        api_url = urljoin(base_url, "/api")
        hass_token = self._get_hass_token(hass_token)
        if not verify_home_assistant_ssl:
            log.warn(
                f"Intentially ignoring Home Assistant's (potentially invalid) SSL certificate. This may leave you vulnerable to a cybersecurity attack. If {base_url} is not a local server, I strongly suggest you 'quit' Fred, enable SSL verification, and try again. Proceed at your own risk."
            )
            import urllib3

            urllib3.disable_warnings(
                category=urllib3.connectionpool.InsecureRequestWarning  # type: ignore[attr-defined]
            )
        return Client(
            api_url=api_url,
            token=hass_token,
            verify_ssl=verify_home_assistant_ssl,
        )

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

    def _get_hass_service_entity_tool_instantiator_func(
        self, domain: Domain, service: Service, entity: Entity, dry_run: bool = False
    ) -> type[BaseTool]:
        entity_friendly_name = entity_friendly_name = (
            entity.state.attributes.get("friendly_name") or entity.slug
        )

        class HassServiceEntityToolArgs(BaseModel):
            pass

        class HassServiceEntityTool(BaseTool):
            name: str = f"{service.service_id}_{entity.entity_id.replace('.', '_')}"  # OpenAI doesn't like periods in tool (function) names
            description: str = f'For {entity_friendly_name}: {service.description or "[description not found]"}'
            return_direct: bool = False
            args_schema: type[BaseModel] = HassServiceEntityToolArgs

            def __str__(self) -> str:
                return f"{self.name=}: {self.description=}"

            def _run(_s) -> str:
                if not dry_run:
                    rich_print(
                        f"\n[italic blue]Calling '{domain.domain_id}.{service.service_id}' on '{entity.entity_id}'.[/italic blue]",
                    )
                    self.hass_client.trigger_service(
                        domain=domain.domain_id,
                        service=service.service_id,
                        entity_id=entity.entity_id,
                    )
                else:
                    log.info(
                        f"Dry run: would have called {domain.domain_id}.{service.service_id} on {entity.entity_id}."
                    )
                return f"Successfully called service {domain.domain_id}.{service.service_id} on {entity_friendly_name}."

        return HassServiceEntityTool

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
                                f"Skipping creating tool for {service.service_id}_{entity.entity_id.replace('.', '_')} because services with fields are not supported yet."
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
                            log.info(f"Created tool {tool.name}: {tool.description}.")

        return wrapped_tools
