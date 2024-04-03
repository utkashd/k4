import logging
import time
from typing import Any, Sequence
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.callbacks import CallbackManagerForChainRun
from langchain_core.utils.input import get_color_mapping
from langchain.agents import AgentExecutor
from langchain.tools import BaseTool

from gpt_home.mutable_tools_openai_tools_agent import MutableToolsOpenAiToolsAgent

log = logging.getLogger("gpt_home")


class MutableToolsAgentExecutor(AgentExecutor):
    def reset_tools(self, tools: list[BaseTool]) -> None:
        """
        Clears all tools from the agent executor and the agent, and then adds the
        provided list of tools to both. Pass an empty list if you just want to remove
        all the tools.
        """
        assert isinstance(self.agent, MutableToolsOpenAiToolsAgent)
        self.tools = tools
        self.agent.reset_tools(tools)

    def _call(
        self,
        inputs: dict[str, str],
        run_manager: CallbackManagerForChainRun | None = None,
    ) -> dict[str, Any]:
        """
        Modified to allow for a mutable tool list.
        Run text through and get agent response.
        """
        intermediate_steps: list[tuple[AgentAction, str]] = []
        # Let's start tracking the number of iterations and time elapsed
        iterations = 0
        time_elapsed = 0.0
        start_time = time.time()
        # We now enter the agent loop (until it returns something).
        while self._should_continue(iterations, time_elapsed):
            next_step_output = self._take_next_step(
                {
                    tool.name: tool for tool in self.tools
                },  # TODO don't redo this work if self.tools hasn't changed
                get_color_mapping(
                    [tool.name for tool in self.tools], excluded_colors=["green", "red"]
                ),  # TODO don't redo this work if self.tools hasn't changed
                inputs,
                intermediate_steps,
                run_manager=run_manager,
            )
            if isinstance(next_step_output, AgentFinish):
                return self._return(
                    next_step_output, intermediate_steps, run_manager=run_manager
                )

            intermediate_steps.extend(next_step_output)
            if (
                len(next_step_output) == 1
            ):  # pretty sure I can remove this entire clause?
                next_step_action = next_step_output[0]
                # See if tool should return directly
                tool_return = self._get_tool_return(next_step_action)
                if tool_return is not None:
                    return self._return(
                        tool_return, intermediate_steps, run_manager=run_manager
                    )
            iterations += 1
            time_elapsed = time.time() - start_time
        output = self.agent.return_stopped_response(
            self.early_stopping_method, intermediate_steps, **inputs
        )
        return self._return(output, intermediate_steps, run_manager=run_manager)

    def add_tools(self, new_tools: Sequence[BaseTool]) -> None:
        assert isinstance(self.agent, MutableToolsOpenAiToolsAgent)
        self.agent.add_tools(new_tools)
        # TODO there's probably a smarter way to combine these two sequences. but these
        # lists should be super short so it doesn't really matter
        new_toolset = [tool for tool in self.tools] + [tool for tool in new_tools]
        if len(new_toolset) > 10:
            log.warn(
                f"Passing more than 10 tools; reliability might not be great with {len(new_toolset)} tools: "
                f"{', '.join([str(tool) for tool in new_toolset])}"
            )
        self.tools = new_toolset
