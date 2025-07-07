from typing import Any, Callable, Literal, TypedDict

import docstring_parser

# from pydantic import BaseModel, Field


# class WeatherInput(BaseModel):
#     location: str = Field(..., description="The city and state, e.g. San Francisco, CA")
#     unit: Literal["celsius", "fahrenheit"] = "fahrenheit"


# def get_current_weather(params: WeatherInput):
#     """Get the current weather in a given location"""
#     return ...


# tool_schema = {
#     "type": "function",
#     "function": {
#         "name": "get_current_weather",
#         "description": get_current_weather.__doc__,
#         "parameters": WeatherInput.model_json_schema(),
#     },
# }


class OpenAiToolJsonFunction(TypedDict):
    name: str
    description: str
    parameters: dict[str, Any]  # TODO type this better, don't use Any


class OpenAiToolJson(TypedDict):
    type: Literal["function"]
    function: OpenAiToolJsonFunction


def convert_python_function_to_openai_tool_json(
    fxn: Callable[..., Any],
) -> OpenAiToolJson:
    fxn_name = fxn.__name__

    assert fxn.__doc__
    fxn_docstring_parsed = docstring_parser.parse(fxn.__doc__)
    fxn_description = (
        fxn_docstring_parsed.short_description
        or fxn_docstring_parsed.long_description
        or fxn_name
    )
    fxn_parameters = {
        param.arg_name: param.type_name for param in fxn_docstring_parsed.params
    }

    # fxn_signature = inspect.signature(fxn) # This + pydantic + .model_schema_json()
    # could be useful for function parameters if docstring parser doesn't work nicely?

    return OpenAiToolJson(
        type="function",
        function={
            "name": fxn_name,
            "description": fxn_description,
            "parameters": fxn_parameters,
        },
    )
