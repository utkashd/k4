import logging
import os
from homeassistant_api import Client, Domain, Group, Service, Entity
from urllib.parse import urljoin
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel
from fred.errors import FredError
from fred.vector_store import VectorStore

log = logging.getLogger("fred")

SUPPORTED_DOMAINS = set(["switch"])


def get_hass_tool_name(service_id: str, entity_id: str) -> str:
    return f"{service_id}_{entity_id.replace('.', '_')}"


def get_hass_tool_description(
    entity_friendly_name: str, service_description: str
) -> str:
    return f"For {entity_friendly_name}: {service_description}"


def create_hass_service_entity_tool(
    hass_client: Client,
    service: Service,
    entity: Entity,
    domain: Domain,
    entity_friendly_name: str,
) -> type[BaseTool]:
    class HassServiceEntityToolArgs(BaseModel):
        pass

    class HassServiceEntityTool(BaseTool):
        name: str = f"{service.service_id}_{entity.entity_id.replace('.', '_')}"  # OpenAI doesn't like periods in tool (function) names
        description: str = f'For {entity_friendly_name}: {service.description or "[description not found]"}'
        return_direct: bool = True
        args_schema: type[BaseModel] = HassServiceEntityToolArgs

        def get_description_for_vector_store(self) -> str:
            return self.description

        def _run(_s) -> str:
            hass_client.trigger_service(
                domain=domain.domain_id,
                service=service.service_id,
                entity_id=entity.entity_id,
            )
            return f"Successfully called {domain.domain_id}.{service.service_id} on {entity_friendly_name}"

    return HassServiceEntityTool


class HomeAssistantToolStore:
    def __init__(self, base_url: str, hass_token: str = ""):
        api_url = urljoin(base_url, "/api")
        hass_token = self._get_hass_token(hass_token)

        # TODO pick one of "home_assistant", "hass", "ha". I keep switching
        self.hass_client = Client(
            api_url=api_url,
            token=hass_token,
        )

        self.vector_store = VectorStore("hass_tools")
        self.domains: dict[str, Domain] = {}
        self.entities: dict[str, Group] = {}
        self.tools: list[BaseTool] = []

        self._get_domains()
        self._get_entities()
        self._create_tools()

        self.vector_store.generate_embeddings_and_save_embeddings_to_db([self.tools])

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
        # self.tools: list[BaseTool] = [
        #     MultiplyTool(),
        #     self.home_assistant_tool_store.get_light_tool(),
        # ]
        return self._get_tools()[:k]

    def _get_domains(self) -> dict[str, Domain]:
        self.domains = self.domains or self.hass_client.get_domains()
        return self.domains

    def _get_entities(self) -> dict[str, Group]:
        self.entities = self.entities or self.hass_client.get_entities()
        return self.entities

    def _get_tools(self) -> list[BaseTool]:
        self.tools = self.tools or self._create_tools()
        return self.tools

    def _create_tools(self) -> list[BaseTool]:
        tools: list[BaseTool] = []
        domains = self._get_domains()
        entities = self._get_entities()

        for domain_id, domain in domains.items():
            if domain_id in SUPPORTED_DOMAINS:
                for entity_slug, entity in entities[domain_id].entities.items():
                    if "utkashs_bedroom_ceiling" in entity_slug:
                        for _, service in domain.services.items():
                            entity_friendly_name = (
                                entity.state.attributes.get("friendly_name")
                                or entity_slug
                            )
                            service_entity_tool = create_hass_service_entity_tool(
                                self.hass_client,
                                service,
                                entity,
                                domain,
                                entity_friendly_name,
                            )
                            tools.append(
                                service_entity_tool(
                                    name=get_hass_tool_name(
                                        service.service_id, entity.entity_id
                                    ),
                                    description=get_hass_tool_description(
                                        entity_friendly_name,
                                        service.description
                                        or "[description not found]",
                                    ),
                                )
                            )
        return tools
