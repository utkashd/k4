from langchain.pydantic_v1 import BaseModel, Field
from langchain.tools import BaseTool
# from langchain.callbacks.manager import CallbackManagerForToolRun


class MultiplyToolArgs(BaseModel):
    a: float = Field("The first number")
    b: float = Field("The second number")


class MultiplyTool(BaseTool):
    name: str = "multiply_tool"
    description: str = "Useful for when you need to multiply two numbers."
    return_direct: bool = False
    args_schema: type[BaseModel] = MultiplyToolArgs

    def _run(
        self,
        a: float,
        b: float,
        # run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        return f"{a * b}"

    # async def _arun(
    #     self, query: str, run_manager: Optional[AsyncCallbackManagerForToolRun] = None
    # ) -> str:
    #     """Use the tool asynchronously."""
    #     raise NotImplementedError("custom_search does not support async")
