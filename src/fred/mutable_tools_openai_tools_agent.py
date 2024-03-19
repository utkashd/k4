from langchain.tools import BaseTool
from langchain.agents.agent import RunnableMultiActionAgent
from typing import Sequence
from langchain_core.runnables import RunnableSequence, RunnableBinding
from langchain_core.utils.function_calling import convert_to_openai_tool


class MutableToolsOpenAiToolsAgent(RunnableMultiActionAgent):
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
        converted_tools = [convert_to_openai_tool(tool) for tool in tools]
        assert isinstance(self.runnable, RunnableSequence)
        assert isinstance(self.runnable.middle[1], RunnableBinding)
        my_kwargs = {**self.runnable.middle[1].kwargs}
        my_kwargs["tools"].extend(converted_tools)
        self.runnable.middle[1].kwargs = my_kwargs
