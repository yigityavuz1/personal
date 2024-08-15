import json
from copy import copy
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
TypedDict,
Annotated
)
from typing_extensions import get_args

from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import (
    BaseMessage,
    FunctionMessage,
    SystemMessage,
HumanMessage
)
from langchain_core.runnables import Runnable, RunnableLambda

import uuid
from langgraph._api.deprecation import deprecated
from langgraph.checkpoint import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.graph.message import add_messages
from langgraph.managed import IsLastStep
from langgraph.prebuilt.tool_executor import ToolExecutor, ToolInvocation

import asyncio
import json
from typing import Any, Callable, Dict, Literal, Optional, Sequence, Union

from langchain_core.messages import AIMessage, AnyMessage, ToolCall, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import get_config_list, get_executor_for_config
from langchain_core.tools import BaseTool, InjectedToolArg
from langchain_core.tools import tool as create_tool

from langgraph.utils import RunnableCallable

INVALID_TOOL_NAME_ERROR_TEMPLATE = (
    "Error: {requested_tool} is not a valid tool, try one of [{available_tools}]."
)
TOOL_CALL_ERROR_TEMPLATE = "Error: {error}\n Please fix your mistakes."

class InjectedState(InjectedToolArg):
    """Annotation for a Tool arg that is meant to be populated with the graph state.

    Any Tool argument annotated with InjectedState will be hidden from a tool-calling
    model, so that the model doesn't attempt to generate the argument. If using
    ToolNode, the appropriate graph state field will be automatically injected into
    the model-generated tool args.

    Args:
        field: The key from state to insert. If None, the entire state is expected to
            be passed in.

    Example:
        ```python
        from typing import List
        from typing_extensions import Annotated, TypedDict

        from langchain_core.messages import BaseMessage, AIMessage
        from langchain_core.tools import tool

        from langgraph.prebuilt import InjectedState, ToolNode


        class AgentState(TypedDict):
            messages: List[BaseMessage]
            foo: str

        @tool
        def state_tool(x: int, state: Annotated[dict, InjectedState]) -> str:
            '''Do something with state.'''
            if len(state["messages"]) > 2:
                return state["foo"] + str(x)
            else:
                return "not enough messages"

        @tool
        def foo_tool(x: int, foo: Annotated[str, InjectedState("foo")]) -> str:
            '''Do something else with state.'''
            return foo + str(x + 1)

        node = ToolNode([state_tool, foo_tool])

        tool_call1 = {"name": "state_tool", "args": {"x": 1}, "id": "1", "type": "tool_call"}
        tool_call2 = {"name": "foo_tool", "args": {"x": 1}, "id": "2", "type": "tool_call"}
        state = {
            "messages": [AIMessage("", tool_calls=[tool_call1, tool_call2])],
            "foo": "bar",
        }
        node.invoke(state)
        ```

        ```pycon
        [
            ToolMessage(content='not enough messages', name='state_tool', tool_call_id='1'),
            ToolMessage(content='bar2', name='foo_tool', tool_call_id='2')
        ]
        ```
    """  # noqa: E501

    def __init__(self, field: Optional[str] = None) -> None:
        self.field = field


def _get_state_args(tool: BaseTool) -> Dict[str, Optional[str]]:
    full_schema = tool.get_input_schema()
    tool_args_to_state_fields: Dict = {}
    for name, type_ in full_schema.__annotations__.items():
        injections = [
            type_arg
            for type_arg in get_args(type_)
            if isinstance(type_arg, InjectedState)
            or (isinstance(type_arg, type) and issubclass(type_arg, InjectedState))
        ]
        if len(injections) > 1:
            raise ValueError(
                "A tool argument should not be annotated with InjectedState more than "
                f"once. Received arg {name} with annotations {injections}."
            )
        elif len(injections) == 1:
            injection = injections[0]
            if isinstance(injection, InjectedState) and injection.field:
                tool_args_to_state_fields[name] = injection.field
            else:
                tool_args_to_state_fields[name] = None
        else:
            pass
    return tool_args_to_state_fields

class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]

    is_last_step: IsLastStep
    tool_call_message: Optional[AIMessage]

def get_change_quantity_verification_message(quantity):
    if quantity == 0:
        return '{} numaralı ürünü sepetten çıkarmak istediğinize emin misiniz? Onaylıyorsanız "evet" deyiniz.'
    else:
        return '{} numaralı ürünün adetini {} olarak değiştirmek istediğinize emin misiniz? Onaylıyorsanız "evet" deyiniz.'

verification_dict = {
    'add_new_product_to_cart': '{} isimli üründen {} {} eklemek istediğinize emin misiniz? Onaylıyorsanız "evet" deyiniz.',
    'empty_cart': 'Sepeti temizlemek istediğinize emin misiniz? Onaylıyorsanız "evet" deyiniz.',
    'redirect_to_payment': 'Alışverişinizi bitirmek istediğinize emin misiniz? Onaylıyorsanız "evet" deyiniz.',
}

def str_output(output: Any) -> str:
    if isinstance(output, str):
        return output
    else:
        try:
            return json.dumps(output)
        except Exception:
            return str(output)


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
# We create the AgentState that we will pass around
# This simply involves a list of messages
# We want steps to return messages to append to the list
# So we annotate the messages attribute with operator.add

def generate_verification_message(message: AIMessage) -> None:
    """Generate "verification message" from message with tool calls."""
    tool_call = message.tool_calls[-1]
    if tool_call['name'] == 'add_new_product_to_cart':
        return AIMessage(
            content=(
                verification_dict['add_new_product_to_cart'].format(
                    tool_call['args']['product_info'],
                    tool_call['args']['quantity'],
                    tool_call['args']['unit']
                )
            ),
            id=message.id,
        )
    elif tool_call['name'] == 'empty_cart':
        return AIMessage(
            content=verification_dict['empty_cart'],
            id=message.id,
        )

    elif tool_call['name'] == 'change_quantity_in_cart':

        return_message = get_change_quantity_verification_message(tool_call['args']['quantity'])
        return AIMessage(
            content=(
                return_message.format(
                    tool_call['args']['product_order'],
                    tool_call['args']['quantity'],
                )
            ),
            id=message.id,
        )
    elif tool_call['name'] == 'redirect_to_payment':
        return AIMessage(
            content=verification_dict['redirect_to_payment'],
            id=message.id,
        )
    else:
        return None


def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }

def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )

def create_react_agent(
    model: LanguageModelLike,
    tools: Union[ToolExecutor, Sequence[BaseTool]],
    messages_modifier: Optional[Union[SystemMessage, str, Callable, Runnable]] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    interrupt_before: Optional[Sequence[str]] = None,
    interrupt_after: Optional[Sequence[str]] = None,
    debug: bool = False,
) -> CompiledGraph:
    """Creates a graph that works with a chat model that utilizes tool calling.
    """

    if isinstance(tools, ToolExecutor):
        tool_classes = tools.tools
    else:
        tool_classes = tools
    model = model.bind_tools(tool_classes)

    # Define the function that determines whether to continue or not
    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        # If there is no function call, then we finish
        if last_message.type == "ai":
            if not last_message.tool_calls:
                return "end"
            else:
                return "continue"
        # Otherwise if there is, we continue
        else:
            return "end"

    # Add the message modifier, if exists
    if messages_modifier is None:
        model_runnable = model
    elif isinstance(messages_modifier, str):
        _system_message: BaseMessage = SystemMessage(content=messages_modifier)
        model_runnable = (lambda messages: [_system_message] + messages) | model
    elif isinstance(messages_modifier, SystemMessage):
        model_runnable = (lambda messages: [messages_modifier] + messages) | model
    elif isinstance(messages_modifier, (Callable, Runnable)):
        model_runnable = messages_modifier | model
    else:
        raise ValueError(
            f"Got unexpected type for `messages_modifier`: {type(messages_modifier)}"
        )

    # Define the function that calls the model
    def call_model(
        state: AgentState,
        config: RunnableConfig,
    ):
        messages = []
        for m in state["messages"][::-1]:
            messages.append(m)
            if len(messages) >= config["configurable"]["max_history"]:
                if messages[-1].type != "tool":
                    break

        messages = messages[::-1]
        AcceptionList = ['evet', 'tamam', 'onay', 'olur', 'tabi','peki','elbette','eet']
        if any(s in messages[-1].content.lower() for s in AcceptionList) and state["tool_call_message"] is not None:
            return {
                "messages": [state["tool_call_message"]],
                "tool_call_message": None,
            }
        else:
            response = model_runnable.invoke(messages, config)

            if response.tool_calls:
                verification_message = generate_verification_message(response)
                if verification_message is not None:
                    response.id = str(uuid.uuid4())
                    return {
                        "messages": [verification_message],
                        "tool_call_message": response,
                    }
                else:
                    return {
                        "messages": [response],
                        "tool_call_message": None,
                    }
            else:
                #if messages[-1].type == 'human':
                #    return {
                #        "messages": [response],
                #        "tool_call_message": None,
                #    }
                #else:
                #    pass
                return {
                        "messages": [response],
                        "tool_call_message": None,
                    }

    async def acall_model(state: AgentState, config: RunnableConfig):
        messages = []
        for m in state["messages"][::-1]:
            messages.append(m)
            if len(messages) >= config["max_history"]:
                if messages[-1].type != "tool":
                    break

        messages = messages[::-1]

        if 'evet' in messages[-1].content.lower() and state["tool_call_message"] is not None:
            return {
                "messages": [state["tool_call_message"]],
                "tool_call_message": None,
            }
        else:
            response = await model_runnable.ainvoke(messages, config)
            if state["is_last_step"] and response.tool_calls:
                return {
                    "messages": [
                        AIMessage(
                            id=response.id,
                            content="Üzgünüm, bunun için çözüm üretemiyorum. Başka bir şey yapmak ister misin?",
                        )
                    ]
                }
            if response.tool_calls:
                verification_message = generate_verification_message(response)
                if verification_message is not None:
                    response.id = str(uuid.uuid4())
                    return {
                        "messages": [verification_message],
                        "tool_call_message": response,
                    }
                else:
                    return {
                        "messages": [response],
                        "tool_call_message": None,
                    }
            else:
                return {
                    "messages": [response],
                    "tool_call_message": None,
                }

    #Create node for checking results from the tool invocations.
    def tool_check(
        state: AgentState,
    ):
        last_tool_call = state['messages'][-1]
        if last_tool_call.artifact:
            if last_tool_call.artifact.get('continue',False):
                return "continue"
            else:
                return "end"
        else:
            return "end"

    def dummy_node(
        state: AgentState,
    ):
        pass
    # Define a new graph
    workflow = StateGraph(AgentState)

    # Define the two nodes we will cycle between
    workflow.add_node("agent", RunnableLambda(call_model, acall_model))
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("post_tool", RunnableLambda(dummy_node))


    # Set the entrypoint as `agent`
    # This means that this node is the first one called
    workflow.set_entry_point("agent")

    # We now add a conditional edge
    workflow.add_conditional_edges(
        # First, we define the start node. We use `agent`.
        # This means these are the edges taken after the `agent` node is called.
        "agent",
        # Next, we pass in the function that will determine which node is called next.
        should_continue,
        # Finally we pass in a mapping.
        # The keys are strings, and the values are other nodes.
        # END is a special node marking that the graph should finish.
        # What will happen is we will call `should_continue`, and then the output of that
        # will be matched against the keys in this mapping.
        # Based on which one it matches, that node will then be called.
        {
            # If `tools`, then we call the tool node.
            "continue": "tools",
            # Otherwise we finish.
            "end": END,
        },
    )

    workflow.add_edge("tools", "post_tool")
    # We now add a normal edge from `tools` to `agent`.
    # This means that after `tools` is called, `agent` node is called next.
    workflow.add_conditional_edges("post_tool",
        tool_check,
                                   {
                                       # If `tools`, then we call the tool node.
                                       "continue": "agent",
                                       # Otherwise we finish.
                                       "end": END,
                                   },
                                   )

    # Finally, we compile it!
    # This compiles it into a LangChain Runnable,
    # meaning you can use it as you would any other runnable
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=interrupt_before,
        interrupt_after=interrupt_after,
        debug=debug,
    )
