from functools import cached_property
import json
import logging
import os
from pathlib import Path
from types import UnionType
import homeassistant_api
import requests
import urllib3
from typing import Any, Optional
from homeassistant_api import Client, Domain, Group, Service, Entity, State
from homeassistant_api.models.domains import ServiceField
from urllib.parse import urljoin
from langchain.tools import BaseTool
from langchain.pydantic_v1 import BaseModel, Field
from pydantic import RootModel, constr
from pydantic import create_model as create_v2_model
from gpt_home.errors import GptHomeError
from gpt_home.mutable_tools_agent_executor import MutableToolsAgentExecutor
from gpt_home.vector_store import VectorStore, VectorStoreItem, VectorStoreItemNotInDb
from rich import print as rich_print
from homeassistant.components.media_player import MediaPlayerEntityFeature  # type: ignore[import-untyped]

log = logging.getLogger("gpt_home")

# SUPPORTED_DOMAINS = {"switch", "media_player"}
# SUPPORTED_DOMAINS = {"*"}
SUPPORTED_DOMAINS = {"switch"}
# SUPPORTED_SERVICE_FIELDS = {"number", "text", "boolean", "select"}


class SerializableHomeAssistantToolWrapper(BaseModel):
    """
    This is useful because a BaseTool can't be put into our vector store, but if it's
    wrapped in this, the relevant metadata can be put into the vector store and we can
    search for the tool quickly.
    """

    domain_id: str
    service_id: str | None = None
    entity_id: str
    name: str  # TODO ensure the name is limited to 64 chars somehow?
    description: str
    hass_tool: BaseTool


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
        directory_to_load_from_and_save_to: Path,
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

        vector_store_tools: list[VectorStoreItemNotInDb] = [
            VectorStoreItemNotInDb(
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
        self.tools_vector_store = VectorStore(
            name="hass_tools",
            directory_to_load_from_and_save_to=directory_to_load_from_and_save_to,
        )
        log.info(
            f"Generating {len(vector_store_tools)} tool embeddings and saving them to the store..."
        )
        self.tools_vector_store.generate_embeddings_and_save_embeddings_to_db(
            vector_store_tools
        )
        log.info(f"Done adding {len(vector_store_tools)} tools to the store.")

    def get_k_relevant_home_assistant_tools(
        self, human_input: str, k: int = 5
    ) -> list[SerializableHomeAssistantToolWrapper]:
        relevant_tools_search_results = (
            self.tools_vector_store.get_top_k_relevant_items_in_db(
                human_input, k
            ).relevant_items_and_scores
        )
        return [
            self._tool_search_result_to_wrapped_tool(tool_search_result.item)
            for tool_search_result in relevant_tools_search_results
        ]

    def get_tool_searcher_tool(
        self,
        agent_executor: MutableToolsAgentExecutor,
    ) -> BaseTool:
        if not self.tool_searcher_tool:
            self.tool_searcher_tool = self._create_tool_searcher_tool(agent_executor)
        return self.tool_searcher_tool

    @cached_property
    def summary_of_tools(self) -> str:
        # num_entities = 0
        # num_domains = 0
        # num_tools = 0

        # s = ""
        # last_tool_index = len(self.tools_vector_store.items) - 1
        # for index, tool in enumerate(self.tools_vector_store.items):
        #     pass
        #     if index == last_tool_index:

        # return f"Of the {num_tools}, "
        return ""

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
            description: str = (
                "Use this to search for more tools if you're not provided an appropriate "
                "tool. If you don't get a good result the first time, retry with a larger "
                "`k` or with a better query, such as by including more context. "
                "You might not get the tool you need, in which case you should inform the "
                "human that you could not find the right tool. "
                f"{self.summary_of_tools}"
            )
            return_direct: bool = False
            args_schema: type[BaseModel] = SearchHassToolsToolArgs

            def __str__(self) -> str:
                return self.name

            def _run(_s, query: str, k: int = 5) -> str:
                rich_print(
                    f"\n[italic blue]Searching for {k=} Home Assistant tools with {query=}.[/italic blue]"
                )
                wrapped_tools = self.get_k_relevant_home_assistant_tools(query, k)
                unwrapped_tools: list[BaseTool] = [
                    wrapped_tool.hass_tool for wrapped_tool in wrapped_tools
                ]
                agent_executor.add_tools(unwrapped_tools)
                rich_print(
                    f"\n[italic blue]Found these tools: {[(wrapped_tool.service_id or 'get state', wrapped_tool.entity_id) for wrapped_tool in wrapped_tools]}[/italic blue]"
                )
                return f"Retrieved {len(unwrapped_tools)} tools: {[unwrapped_tool.name for unwrapped_tool in unwrapped_tools]}"

        self.tool_searcher_tool = SearchHassToolsTool()
        return self.tool_searcher_tool

    def _create_hass_client(
        self, base_url: str, hass_token: str, verify_home_assistant_ssl: bool = True
    ) -> Client:
        api_url = urljoin(base_url, "/api")
        hass_token = self._get_hass_token(hass_token)

        if not verify_home_assistant_ssl:
            log.warn(
                "Intentially ignoring Home Assistant's (potentially invalid) SSL "
                "certificate. This may leave you vulnerable to a cyberattack. If "
                f"{base_url} is not a local server, I strongly suggest you 'quit' GptHome,"
                " enable SSL verification, and try again. Proceed at your own risk."
            )
            urllib3.disable_warnings(
                category=urllib3.connectionpool.InsecureRequestWarning  # type: ignore[attr-defined]
            )

        client = Client(
            api_url=api_url,
            token=hass_token,
            verify_ssl=verify_home_assistant_ssl,
        )
        try:
            client.get_config()  # if the client
        except requests.exceptions.SSLError as ssl_error:
            error = GptHomeError(
                "Failed to create a Home Assistant API client due to SSL certificate "
                "issues. If you don't have a valid SSL certificate for your Home "
                "Assistant instance, you can skip verifying the SSL certificate by "
                'setting the environment variable `GPT_HOME_HA_IGNORE_SSL="true"`'
            )
            log.exception(error)
            log.debug(f"{base_url=}, {api_url=}, {verify_home_assistant_ssl=}")
            raise error from ssl_error
        return client

    def _get_hass_token(self, hass_token: str) -> str:
        if hass_token == "":
            hass_environment_variable_value = os.environ.get("GPT_HOME_HA_TOKEN")
            if not hass_environment_variable_value:
                raise GptHomeError(
                    "No Home Assistant API token was provided and there is no environment variable. Please provide one or set the environment variable `GPT_HOME_HA_TOKEN`."
                )
            else:
                hass_token = hass_environment_variable_value
        return hass_token

    def _get_hass_entity_state_tool_instantiator_func(
        self, entity: Entity, dry_run: bool = False
    ) -> type[BaseTool]:
        entity_friendly_name = (
            entity.state.attributes.get("friendly_name") or entity.slug
        )

        class HassEntityStateToolArgs(BaseModel):
            pass

        class HassEntityStateTool(BaseTool):
            name: str = f"get_state_{entity.entity_id.replace('.', '_')}"
            description: str = f"Get state/attributes of {entity_friendly_name}"
            return_direct: bool = False
            args_schema: type[BaseModel] = HassEntityStateToolArgs

            def __str__(self) -> str:
                return self.name

            def _run(_s) -> str:
                # Since we're only reading an entity's state, we'll always get the
                # entity state and ignore whether this is a dry-run.
                rich_print(
                    f"\n[italic blue]Getting the state of {entity.entity_id}.[/italic blue]"
                )
                latest_entity_info = self.hass_client.get_entity(
                    entity_id=entity.entity_id
                )
                if latest_entity_info is None:
                    raise GptHomeError(f"Failed to get the state of {entity=}")

                formatted_entity_state = self._format_entity_state(
                    latest_entity_info.state
                )
                rich_print(f"\n[italic blue]{formatted_entity_state}[/italic blue]")
                return formatted_entity_state

        return HassEntityStateTool

    def _format_entity_state(self, entity_state: State) -> str:
        readable_entity_state_obj = {
            "entity_id": entity_state.entity_id,
            "state": entity_state.state,
            "attributes": entity_state.attributes,  # assumed to be readable already
        }
        if entity_state.last_updated:
            readable_entity_state_obj["last_updated"] = (
                entity_state.last_updated.strftime("%d/%m %H:%M %Z"),
            )  # TODO format this better. assuming americans rn

        if entity_state.last_changed:
            readable_entity_state_obj["last_changed"] = (
                entity_state.last_changed.strftime("%d/%m %H:%M %Z"),
            )  # TODO format this better. assuming americans rn

        return json.dumps(readable_entity_state_obj, indent=4)

    def _get_field_type(self, service_field: ServiceField) -> type | UnionType:
        """
        See https://www.home-assistant.io/docs/blueprint/selectors/

        Parameters
        ----------
        service_field : ServiceField

        Returns
        -------
        type
            A Python type roughly equivalent to the selector of the provided ServiceField
        """
        original_type: type = str  # assume string by default?
        if service_field.selector:
            selector_type: str = next(iter(service_field.selector.keys()))
            selector_details: dict[str, Any] | None = next(
                iter(service_field.selector.values())
            )
            match selector_type:
                case "number":
                    # TODO: use the selector data to determine int vs float
                    original_type = float
                case "text":
                    original_type = str
                case "select":
                    if not selector_details or "options" not in selector_details.keys():
                        log.warning(
                            f"Unexpectedly didn't find `options` in the selector details. {service_field=}"
                        )
                        original_type = str
                    else:
                        options = selector_details["options"]

                        # class Selector_Options:
                        #     def __init__(options_self, value: str) -> None:
                        #         if value not in options:
                        #             raise ValueError(
                        #                 f"Invalid literal: {value}. Must be one of {options=}"
                        #             )
                        #         self.value = value

                        original_type = constr(pattern="|".join(options))
                case "theme":
                    log.warning(
                        f"Untested selector type {selector_type=}, {service_field=}\nThis hasn't been implemented yet."
                    )
                    original_type = str
                case "boolean":
                    original_type = bool
                case "object":
                    original_type = object
                case "addon":
                    log.warning(
                        f"Untested selector type {selector_type=}, {service_field=}\nThis hasn't been implemented yet."
                    )
                    original_type = str
                case "backup_location":
                    log.warning(
                        f"Untested selector type {selector_type=}, {service_field=}\nThis hasn't been implemented yet."
                    )
                    original_type = str
                case "entity":
                    # this and time seem to be the majority of untested types?
                    log.warning(
                        f"Untested selector type {selector_type=}, {service_field=}\nThis hasn't been implemented yet."
                    )
                    original_type = Entity
                case "conversation_agent":
                    log.warning(
                        f"Untested selector type {selector_type=}, {service_field=}\nThis hasn't been implemented yet."
                    )
                    original_type = str
                case "icon":
                    log.warning(
                        f"Untested selector type {selector_type=}, {service_field=}\nThis hasn't been implemented yet."
                    )
                    original_type = str
                case "time":
                    log.warning(
                        f"Untested selector type {selector_type=}, {service_field=}\nThis hasn't been implemented yet."
                    )
                    original_type = str
                case "color_rgb":
                    log.warning(
                        f"Untested selector type {selector_type=}, {service_field=}\nThis hasn't been implemented yet."
                    )
                    original_type = str
                case "color_temp":
                    log.warning(
                        f"Untested selector type {selector_type=}, {service_field=}\nThis hasn't been implemented yet."
                    )
                    original_type = int
                case "constant":
                    pass
                case "template":
                    log.warning(
                        f"Untested selector type {selector_type=}, {service_field=}\nThis hasn't been implemented yet."
                    )
                    original_type = str
                case _:
                    log.warning(
                        f"Unexpectedly did not match a selector. {selector_type=}, {service_field=}"
                    )

        return original_type

    def _get_hass_service_entity_tool_instantiator_func_with_params(
        self, domain: Domain, service: Service, entity: Entity, dry_run: bool = False
    ) -> type[BaseTool]:
        if not service.fields:
            log.warning(
                f"Unexpectedly attempted to create a tool with parameters, but the service doesn't have any parameters: {domain.domain_id}.{service.service_id}"
            )
            return self._get_hass_service_entity_tool_instantiator_func(
                domain, service, entity, dry_run=dry_run
            )

        field_definitions: dict[str, Any] = {}
        for field_name, service_field in service.fields.items():
            field_type = self._get_field_type(service_field)
            field_description = f"{service_field.description}"
            if service_field.example:
                field_description += f" Example: {service_field.example}"
            # TODO better default? it's currently None
            field = Field(
                None, description=field_description, required=service_field.required
            )

            field_definitions[field_name] = (
                field_type,
                field,
            )

        HassServiceEntityToolWithParamsArgs = create_v2_model(
            "HassServiceEntityToolWithParamsArgs", **field_definitions
        )

        entity_friendly_name = (
            entity.state.attributes.get("friendly_name") or entity.slug
        )

        class HassServiceEntityToolWithParams(BaseTool):
            name: str = f"{service.service_id}_{entity.entity_id.replace('.', '_')}"  # OpenAI doesn't like periods in tool (function) names
            description: str = f'For {entity_friendly_name}: {service.description or "[description not found]"}'
            return_direct: bool = False
            args_schema: type[BaseModel] = HassServiceEntityToolWithParamsArgs

            def __str__(self) -> str:
                return self.name

            def _run(_s, **service_data: dict[str, Any]) -> str:
                if not dry_run:
                    rich_print(
                        f"\n[italic blue]Calling {domain.domain_id}.{service.service_id} on {entity.entity_id} with {service_data}.[/italic blue]",
                    )
                    try:
                        self.hass_client.trigger_service(
                            domain=domain.domain_id,
                            service=service.service_id,
                            entity_id=entity.entity_id,
                            **service_data,
                        )
                    except homeassistant_api.errors.InternalServerError:
                        failure_message = f"Failed to call {domain.domain_id}.{service.service_id} on {entity_friendly_name} with {service_data}"
                        log.exception(
                            failure_message,
                            exc_info=True,
                        )
                        return failure_message
                else:
                    log.info(
                        f"Dry run: would have called {domain.domain_id}.{service.service_id} on {entity.entity_id} with {service_data}."
                    )
                return f"Successfully called service {domain.domain_id}.{service.service_id} on {entity_friendly_name} with {service_data}."

        #  **service_data: dict[str, Any]

        return HassServiceEntityToolWithParams

    def _get_hass_service_entity_tool_instantiator_func(
        self, domain: Domain, service: Service, entity: Entity, dry_run: bool = False
    ) -> type[BaseTool]:
        class HassServiceEntityToolArgs(BaseModel):
            pass

        entity_friendly_name = (
            entity.state.attributes.get("friendly_name") or entity.slug
        )

        class HassServiceEntityTool(BaseTool):
            name: str = f"{service.service_id}_{entity.entity_id.replace('.', '_')}"  # OpenAI doesn't like periods in tool (function) names
            description: str = f'For {entity_friendly_name}: {service.description or "[description not found]"}'
            return_direct: bool = False
            args_schema: type[BaseModel] = HassServiceEntityToolArgs

            def __str__(self) -> str:
                return self.name

            def _run(_s) -> str:
                if not dry_run:
                    rich_print(
                        f"\n[italic blue]Calling {domain.domain_id}.{service.service_id} on {entity.entity_id}.[/italic blue]",
                    )
                    try:
                        self.hass_client.trigger_service(
                            domain=domain.domain_id,
                            service=service.service_id,
                            entity_id=entity.entity_id,
                        )
                    except homeassistant_api.errors.InternalServerError:
                        failure_message = f"Failed to call {domain.domain_id}.{service.service_id} on {entity_friendly_name}"
                        log.exception(
                            failure_message,
                            exc_info=True,
                        )
                        return failure_message
                else:
                    log.info(
                        f"Dry run: would have called {domain.domain_id}.{service.service_id} on {entity.entity_id}."
                    )
                return f"Successfully called service {domain.domain_id}.{service.service_id} on {entity_friendly_name}."

        return HassServiceEntityTool

    def _tool_search_result_to_wrapped_tool(
        self, tool_search_result: VectorStoreItem
    ) -> SerializableHomeAssistantToolWrapper:
        return self.wrapped_tools[tool_search_result.metadata["name"]]

    def _get_domains(self) -> dict[str, Domain]:
        if self.domains:
            return self.domains

        domains_filename = "hass_domains.json"
        if False and os.path.exists(
            domains_filename
        ):  # this isn't implemented yet, sorry
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
                f"No existing {domains_filename} found (because that isn't implemented yet—this is normal). Hitting the Home Assistant API for domains."
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
        if False and os.path.exists(
            entities_filename
        ):  # this isn't implemented yet, sorry
            log.info(f"Loading the existing hass entities from {entities_filename}.")
            with open(entities_filename, "r") as entities_file:
                self.entities = json.load(entities_file)  # this needs fixing
        else:
            log.info(
                f"No existing {entities_filename} found (because that isn't implemented yet—this is normal). Hitting the Home Assistant API for entities."
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
        entity_to_supported_services: dict[str, list[str]] = {}

        def _does_entity_support_service(
            domain: Domain, service: Service, entity: Entity
        ) -> bool:
            """
            Helper function that determines whether an entity supports a particular
            service.

            This is necessary because Home Assistant implements "which services does X
            entity support?" very strangely. `supported_features` is an integer which
            represents the sum of a bunch of powers of 2. Each power of 2 in there maps
            to a service. See
            https://github.com/home-assistant/core/blob/cabc4f797ae4f3b839e60248cb6da216acfe22b6/homeassistant/components/media_player/const.py#L178

            So `supported_features=5` means the entity supports services 1 and 4,
            `supported_features=26` means the entity supports services 2, 8 and 16, etc.
            """
            if entity_to_supported_services.get(entity.entity_id):
                return (
                    service.service_id in entity_to_supported_services[entity.entity_id]
                )
            entity_to_supported_services[entity.entity_id] = []
            match domain.domain_id:
                case "switch":
                    # switches don't have "supported features," i.e., all are always supported
                    return True
                case "media_player":
                    if entity.state.attributes.get("supported_features"):
                        supported_features_int = entity.state.attributes[
                            "supported_features"
                        ]
                        binary_string_supported_features = bin(supported_features_int)

                        for index, char in enumerate(
                            binary_string_supported_features[:1:-1]
                        ):  # iterate backwards, ignore the "this is a binary number" prefix "0b"
                            if char == "1":
                                media_player_service = MediaPlayerEntityFeature(
                                    2**index
                                )
                                match media_player_service:
                                    case MediaPlayerEntityFeature.PAUSE:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("media_pause")
                                    case MediaPlayerEntityFeature.SEEK:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("media_seek")
                                    case MediaPlayerEntityFeature.VOLUME_SET:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("volume_set")
                                    case MediaPlayerEntityFeature.VOLUME_MUTE:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("volume_mute")
                                    case MediaPlayerEntityFeature.VOLUME_MUTE:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("volume_mute")
                                    case MediaPlayerEntityFeature.PREVIOUS_TRACK:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("media_previous_track")
                                    case MediaPlayerEntityFeature.NEXT_TRACK:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("media_next_track")
                                    case MediaPlayerEntityFeature.TURN_ON:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("turn_on")
                                    case MediaPlayerEntityFeature.TURN_OFF:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("turn_off")
                                    case MediaPlayerEntityFeature.PLAY_MEDIA:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("play_media")
                                    case MediaPlayerEntityFeature.VOLUME_STEP:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].extend(["volume_up", "volume_down"])
                                    case MediaPlayerEntityFeature.SELECT_SOURCE:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("select_source")
                                    case MediaPlayerEntityFeature.STOP:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("media_stop")
                                    case MediaPlayerEntityFeature.CLEAR_PLAYLIST:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("clear_playlist")
                                    case MediaPlayerEntityFeature.PLAY:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("media_play")
                                    case MediaPlayerEntityFeature.SHUFFLE_SET:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("shuffle_set")
                                    case MediaPlayerEntityFeature.SELECT_SOUND_MODE:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("select_sound_mode")
                                    case MediaPlayerEntityFeature.BROWSE_MEDIA:
                                        log.warn(
                                            f"Unimplemented service {media_player_service=}"
                                        )  # TODO implement
                                    case MediaPlayerEntityFeature.REPEAT_SET:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("repeat_set")
                                    case MediaPlayerEntityFeature.GROUPING:
                                        entity_to_supported_services[
                                            entity.entity_id
                                        ].append("join")
                                    case MediaPlayerEntityFeature.MEDIA_ANNOUNCE:
                                        log.warn(
                                            f"Unimplemented service {media_player_service=}"
                                        )  # TODO implement
                                    case MediaPlayerEntityFeature.MEDIA_ENQUEUE:
                                        log.warn(
                                            f"Unimplemented service {media_player_service=}"
                                        )  # TODO implement
                        return (
                            service.service_id
                            in entity_to_supported_services[entity.entity_id]
                        )
                    else:
                        log.warn(
                            f'Entity {entity.entity_id} does not have a "supported_features" attribute. Assuming all services are supported.'
                        )
                        return True
                case _:
                    log.warn(
                        f"Unimplemented domain {domain.domain_id}. Going to (unsafely) assume that all services are supported for {entity.entity_id}"
                    )
                    return True

        wrapped_tools: dict[str, SerializableHomeAssistantToolWrapper] = {}
        domains = self._get_domains()
        entities = self._get_entities()

        # create tools for getting entity states
        for group_id, entity_group in entities.items():
            if group_id in SUPPORTED_DOMAINS or "*" in SUPPORTED_DOMAINS:
                for entity_slug, entity in entity_group.entities.items():
                    tool_name = f"get_state_{entity.entity_id.replace('.', '_')}"
                    tool_description = f'Get state/attributes of {entity.state.attributes.get("friendly_name") or entity_slug}'
                    if len(tool_name) > 64:
                        log.info(
                            f"Skipping creating a tool for getting the state of {entity.entity_id} because the tool's name would be too long and I haven't fixed that bug yet."
                        )
                    else:
                        log.info(
                            f"Creating a tool to get the state of {entity.entity_id}..."
                        )
                        get_hass_entity_state_tool = (
                            self._get_hass_entity_state_tool_instantiator_func(
                                entity, dry_run=self.dry_run
                            )
                        )

                        get_entity_state_tool: BaseTool = get_hass_entity_state_tool(
                            name=tool_name,
                            description=tool_description,
                        )
                        wrapped_tools[get_entity_state_tool.name] = (
                            SerializableHomeAssistantToolWrapper(
                                domain_id=group_id,
                                service_id=None,
                                entity_id=entity.entity_id,
                                name=get_entity_state_tool.name,
                                description=get_entity_state_tool.description,
                                hass_tool=get_entity_state_tool,
                            )
                        )
                        log.info(
                            f"Created tool {get_entity_state_tool.name}: {get_entity_state_tool.description}."
                        )

        # create tools for calling services on entities
        for domain_id, domain in domains.items():
            if (
                domain_id in SUPPORTED_DOMAINS or "*" in SUPPORTED_DOMAINS
            ) and domain_id in entities.keys():
                for entity_slug, entity in entities[domain_id].entities.items():
                    for _, service in domain.services.items():
                        tool_name = (
                            f"{service.service_id}_{entity.entity_id.replace('.', '_')}"
                        )
                        tool_description = f'For {entity.state.attributes.get("friendly_name") or entity_slug}: {service.description or "[description not found]"}'
                        if len(tool_name) > 64:
                            log.info(
                                f"Skipping creating a tool for calling {domain.domain_id}.{service.service_id} on {entity.entity_id} because the tool's name would be too long and I haven't fixed that bug yet."
                            )
                        elif service.service_id == "toggle":
                            log.info(
                                f"Skipping creating a tool for calling {domain.domain_id}.toggle on {entity.entity_id} because the LLM likes to use the toggle tools too much and I want to get it to do explicit `turn on` or `turn off` first."
                            )
                        elif domain.domain_id == "remote":
                            log.info(
                                "Skipping creating a tool for anything `remote`-related because it's not useful (yet?)."
                            )
                        elif not _does_entity_support_service(domain, service, entity):
                            log.info(
                                f"Skipping creating a tool for {domain.domain_id}.{service.service_id} on {entity.entity_id} because that entity does not support that service."
                            )
                        else:
                            log.info(
                                f"Creating a tool for calling {domain.domain_id}.{service.service_id} on {entity.entity_id}..."
                            )
                            if service.fields:
                                # log.info(
                                #     f"Skipped creating tool {service.service_id}_{entity.entity_id.replace('.', '_')} because we don't support fields yet."
                                # )
                                get_hass_service_entity_tool = self._get_hass_service_entity_tool_instantiator_func_with_params(
                                    domain, service, entity, dry_run=self.dry_run
                                )
                            else:
                                get_hass_service_entity_tool = self._get_hass_service_entity_tool_instantiator_func(
                                    domain, service, entity, dry_run=self.dry_run
                                )
                            call_service_on_entity_tool: BaseTool = (
                                get_hass_service_entity_tool(
                                    name=tool_name,
                                    description=tool_description,
                                )
                            )
                            wrapped_tools[call_service_on_entity_tool.name] = (
                                SerializableHomeAssistantToolWrapper(
                                    domain_id=domain.domain_id,
                                    service_id=service.service_id,
                                    entity_id=entity.entity_id,
                                    name=call_service_on_entity_tool.name,
                                    description=call_service_on_entity_tool.description,
                                    hass_tool=call_service_on_entity_tool,
                                )
                            )
                            log.info(
                                f"Created tool {call_service_on_entity_tool.name}: {call_service_on_entity_tool.description}."
                            )

        return wrapped_tools
