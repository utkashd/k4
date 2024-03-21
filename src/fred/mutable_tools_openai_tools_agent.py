from langchain.tools import BaseTool
from langchain.agents.agent import RunnableMultiActionAgent
from typing import Any, Sequence
from langchain_core.runnables import RunnableSequence, RunnableBinding
from langchain_core.utils.function_calling import convert_to_openai_tool


class MutableToolsOpenAiToolsAgent(RunnableMultiActionAgent):
    def convert_to_openai_tool(self, tool: BaseTool) -> dict[str, Any]:
        # if (
        #     tool.args_schema
        #     and tool.args_schema.__fields__
        #     and tool.args_schema.__fields__.get("field_definitions")
        # ):
        #     # the langchain version of this function fails if the tool has parameters.
        #     # I'm probably doing something wrong to cause it (maybe?), but this is a
        #     # workaround I'm willing to live with for now
        #     # ok now that I'm coding this, I'm not sure it's worth it anymore. but I
        #     # don't want to think of the right solution rn
        #     tool_parameters_json_serializable: dict[str, dict[str, str]] = {}
        #     assert isinstance(
        #         tool.args_schema.__fields__["field_definitions"].default,
        #         dict,
        #     )
        #     for (
        #         parameter_name,
        #         type_and_field_info_tuple,
        #     ) in tool.args_schema.__fields__["field_definitions"].default.items():
        #         assert isinstance(type_and_field_info_tuple, tuple)
        #         assert isinstance(type_and_field_info_tuple[0], type)
        #         tool_parameters_json_serializable[parameter_name] = {
        #             "type": type(type_and_field_info_tuple[0]).__name__,
        #             "description": type_and_field_info_tuple[1].description,
        #         }
        #     return {
        #         "type": "function",
        #         "function": {
        #             "name": tool.name,
        #             "description": tool.description,
        #             "parameters": {
        #                 "type": "object",
        #                 "properties": tool_parameters_json_serializable,
        #             },
        #         },
        #     }
        # return {}
        return convert_to_openai_tool(tool)

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
