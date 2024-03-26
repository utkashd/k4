from langchain.tools import BaseTool
from langchain.agents.agent import RunnableMultiActionAgent
from typing import Any, Sequence
from langchain_core.runnables import RunnableSequence, RunnableBinding
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic.json_schema import GenerateJsonSchema
# from pydantic.fields import FieldInfo


class MutableToolsOpenAiToolsAgent(RunnableMultiActionAgent):
    def _convert_python_type_to_openai_string(self, python_type: type) -> str:
        name = python_type.__name__
        if name == "float":
            return "number"
        elif name == "str":
            return "string"
        elif name == "bool":
            return "boolean"
        return name

    def convert_to_openai_tool(self, tool: BaseTool) -> dict[str, Any]:
        # ignore warnings stemming from how I create tools with parameters
        GenerateJsonSchema.ignored_warning_kinds = {"non-serializable-default"}
        converted_tool = convert_to_openai_tool(tool)
        # we have to do special stuff if the tool has parameters because I'm using
        # Pydantic v2 for the args schema for those tools. so there's janky stuff like
        # "trust me it's a FieldInfo and not a ModelField"
        if (
            tool.args_schema
            and tool.args_schema.__fields__
            and tool.args_schema.__name__ == "HassServiceEntityToolWithParamsArgs"
        ):
            properties: dict[str, Any] = {}
            required_properties: list[str] = []
            for field_name, field_info in tool.args_schema.__fields__.items():
                assert hasattr(
                    field_info, "is_required"
                )  # it's a FieldInfo, not a ModelField
                if field_info.is_required():
                    required_properties.append(field_name)
                properties[field_name] = {
                    "description": field_info.default.description,
                    # "default":
                    "type": self._convert_python_type_to_openai_string(
                        field_info.annotation
                    ),
                }
            converted_tool["function"]["parameters"]["properties"] = properties
            converted_tool["function"]["parameters"]["required"] = required_properties
        return converted_tool

    def reset_tools(self, tools: list[BaseTool]) -> None:
        self.clear_tools()
        self.add_tools(tools)

    def clear_tools(self) -> None:
        assert isinstance(self.runnable, RunnableSequence)
        assert isinstance(self.runnable.middle[1], RunnableBinding)
        my_kwargs = {**self.runnable.middle[1].kwargs}
        my_kwargs["tools"] = []
        self.runnable.middle[1].kwargs = my_kwargs

    def add_tools(self, tools: Sequence[BaseTool]) -> None:
        converted_tools = [self.convert_to_openai_tool(tool) for tool in tools]
        assert isinstance(self.runnable, RunnableSequence)
        assert isinstance(self.runnable.middle[1], RunnableBinding)
        my_kwargs = {**self.runnable.middle[1].kwargs}
        my_kwargs["tools"].extend(converted_tools)
        self.runnable.middle[1].kwargs = my_kwargs
