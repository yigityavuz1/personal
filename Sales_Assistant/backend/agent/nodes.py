import asyncio
from copy import copy
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    ToolCall,
    ToolMessage
)
from langchain_core.runnables import RunnableConfig, get_config_list
from langchain_core.runnables.config import get_executor_for_config
from langchain_core.tools import BaseTool
from langchain_core.tools import tool as create_tool
from langgraph.utils import RunnableCallable
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union
)

from .helper_functions import str_output, _get_state_args
from .templates import (
    INVALID_TOOL_NAME_ERROR_TEMPLATE,
    TOOL_CALL_ERROR_TEMPLATE
)


class ToolNode(RunnableCallable):
    """A node that runs the tools called in the last AIMessage.

    It can be used either in StateGraph with a "messages" key or in MessageGraph. If
    multiple tool calls are requested, they will be run in parallel. The output will be
    a list of ToolMessages, one for each tool call.

    The `ToolNode` is roughly analogous to:

    ```python
    tools_by_name = {tool.name: tool for tool in tools}
    def tool_node(state: dict):
        result = []
        for tool_call in state["messages"][-1].tool_calls:
            tool = tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])
            result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
        return {"messages": result}
    ```

    Important:
        - The state MUST contain a list of messages.
        - The last message MUST be an `AIMessage`.
        - The `AIMessage` MUST have `tool_calls` populated.
    """

    def __init__(
        self,
        tools: Sequence[Union[BaseTool, Callable]],
        *,
        name: str = "tools",
        tags: Optional[list[str]] = None,
        handle_tool_errors: Optional[bool] = True,
    ) -> None:
        super().__init__(self._func, self._afunc, name=name, tags=tags, trace=False)
        self.tools_by_name: Dict[str, BaseTool] = {}
        self.handle_tool_errors = handle_tool_errors
        for tool_ in tools:
            if not isinstance(tool_, BaseTool):
                tool_ = create_tool(tool_)
            self.tools_by_name[tool_.name] = tool_

    def _func(
        self, input: Union[list[AnyMessage], dict[str, Any]], config: RunnableConfig
    ) -> Any:
        tool_calls, output_type = self._parse_input(input)
        config_list = get_config_list(config, len(tool_calls))
        with get_executor_for_config(config) as executor:
            outputs = [*executor.map(self._run_one, tool_calls, config_list)]
        return outputs if output_type == "list" else {"messages": outputs}

    async def _afunc(
        self, input: Union[list[AnyMessage], dict[str, Any]], config: RunnableConfig
    ) -> Any:
        tool_calls, output_type = self._parse_input(input)
        outputs = await asyncio.gather(
            *(self._arun_one(call, config) for call in tool_calls)
        )
        return outputs if output_type == "list" else {"messages": outputs}

    def _run_one(self, call: ToolCall, config: RunnableConfig) -> ToolMessage:
        if invalid_tool_message := self._validate_tool_call(call):
            return invalid_tool_message

        try:
            input = {**call, **{"type": "tool_call"}}
            tool_message: ToolMessage = self.tools_by_name[call["name"]].invoke(
                input, config
            )
            # TODO: handle this properly in core
            tool_message.content = str_output(tool_message.content)
            return tool_message
        except Exception as e:
            if not self.handle_tool_errors:
                raise e
            content = TOOL_CALL_ERROR_TEMPLATE.format(error=repr(e))
            return ToolMessage(content, name=call["name"], tool_call_id=call["id"])

    async def _arun_one(self, call: ToolCall, config: RunnableConfig) -> ToolMessage:
        if invalid_tool_message := self._validate_tool_call(call):
            return invalid_tool_message
        try:
            input = {**call, **{"type": "tool_call"}}
            tool_message: ToolMessage = await self.tools_by_name[call["name"]].ainvoke(
                input, config
            )
            # TODO: handle this properly in core
            tool_message.content = str_output(tool_message.content)
            return tool_message
        except Exception as e:
            if not self.handle_tool_errors:
                raise e
            content = TOOL_CALL_ERROR_TEMPLATE.format(error=repr(e))
            return ToolMessage(content, name=call["name"], tool_call_id=call["id"])

    def _parse_input(
        self, input: Union[list[AnyMessage], dict[str, Any]]
    ) -> Tuple[List[ToolCall], Literal["list", "dict"]]:
        if isinstance(input, list):
            output_type = "list"
            message: AnyMessage = input[-1]
        elif messages := input.get("messages", []):
            output_type = "dict"
            message = messages[-1]
        else:
            raise ValueError("No message found in input")

        if not isinstance(message, AIMessage):
            raise ValueError("Last message is not an AIMessage")

        tool_calls = [
            self._inject_state(call, input)
            for call in cast(AIMessage, message).tool_calls
        ]
        return tool_calls, output_type

    def _validate_tool_call(self, call: ToolCall) -> Optional[ToolMessage]:
        if (requested_tool := call["name"]) not in self.tools_by_name:
            content = INVALID_TOOL_NAME_ERROR_TEMPLATE.format(
                requested_tool=requested_tool,
                available_tools=", ".join(self.tools_by_name.keys()),
            )
            return ToolMessage(content, name=requested_tool, tool_call_id=call["id"])
        else:
            return None

    def _inject_state(
        self, tool_call: ToolCall, input: Union[list[AnyMessage], dict[str, Any]]
    ) -> ToolCall:
        if tool_call["name"] not in self.tools_by_name:
            return tool_call
        state_args = _get_state_args(self.tools_by_name[tool_call["name"]])
        if state_args and not isinstance(input, dict):
            required_fields = list(state_args.values())
            if (
                len(required_fields) == 1
                and required_fields[0] == "messages"
                or required_fields[0] is None
            ):
                input = {"messages": input}
            else:
                err_msg = (
                    f"Invalid input to ToolNode. Tool {tool_call['name']} requires "
                    f"graph state dict as input."
                )
                if any(state_field for state_field in state_args.values()):
                    required_fields_str = ", ".join(f for f in required_fields if f)
                    err_msg += f" State should contain fields {required_fields_str}."
                raise ValueError(err_msg)
        tool_call_copy: ToolCall = copy(tool_call)
        tool_call_copy["args"] = {
            **tool_call_copy["args"],
            **{
                tool_arg: cast(dict, input)[state_field] if state_field else input
                for tool_arg, state_field in state_args.items()
            },
        }
        return tool_call_copy