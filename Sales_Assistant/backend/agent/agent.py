from azure.search.documents._generated.models import VectorizedQuery
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    SystemMessage
)
from langchain_core.language_models import LanguageModelLike
from langchain_core.runnables import RunnableLambda, Runnable, RunnableConfig
from langchain_core.tools import BaseTool, StructuredTool
from langchain.pydantic_v1 import Field, create_model
from langgraph.checkpoint import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.graph import CompiledGraph
from typing import (
    Annotated,
    Callable,
    Dict,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union
)
from langgraph.prebuilt import ToolExecutor
import random
import uuid

from . import templates
from .nodes import ToolNode
from .prompts import LLM_SYSTEM_MESSAGE, EntityExtractorPrompt, SUPERVISOR_SYSTEM_MESSAGE
from .states import AgentState, InjectedState
from .helper_functions import TurkishStr, entity_output_parser
import json
import requests



def get_change_unit_verification_message(unit):
    if unit is  None or unit == 'None' or unit == -1:
       return templates.ADD_NEW_PRODUCT_TO_CART_ADET_VERIFICATION
    else:
        return templates.ADD_NEW_PRODUCT_TO_CART_VERIFICATION


def get_change_quantity_verification_message(quantity):
    if quantity == 0:
        return templates.REMOVE_PRODUCT_FROM_CART_VERIFICATION
    else:
        return templates.CHANGE_QUANTITY_VERIFICATION

def generate_verification_message(message: AIMessage) -> None:
    """Generate "verification message" from message with tool calls."""
    tool_call = message.tool_calls[-1]
    if tool_call['name'] == 'add_new_product_to_cart':
        return_message2 = get_change_unit_verification_message(tool_call['args']['unit'])
        return AIMessage(
            content=(
                return_message2.format(
                    tool_call['args']['product_info'],
                    tool_call['args']['quantity'],
                    tool_call['args']['unit']
                )
            ),
            id=message.id,
        )
    elif tool_call['name'] == 'empty_cart':
        return AIMessage(
            content=templates.EMPTY_CART_VERIFICATION,
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
            content=templates.REDIRECT_TO_PAYMENT_VERIFICATION,
            id=message.id,
        )
    else:
        return None


def create_react_agent(
    model: LanguageModelLike,
    tools: Union[ToolExecutor, Sequence[BaseTool]],
    messages_modifier: Optional[Union[SystemMessage, str, Callable, Runnable]] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    interrupt_before: Optional[Sequence[str]] = None,
    interrupt_after: Optional[Sequence[str]] = None,
    debug: bool = False,
    planner_tools: Union[ToolExecutor, Sequence[BaseTool]] = None,
    planner_messages_modifier: Optional[Union[SystemMessage, str, Callable, Runnable]] = None,
) -> CompiledGraph:
    """Creates a graph that works with a chat model that utilizes tool calling.
    """
    from copy import copy
    if isinstance(tools, ToolExecutor):
        tool_classes = tools.tools
    else:
        tool_classes = tools
    agent_model = copy(model).bind_tools(tool_classes)


    # Add the message modifier, if exists
    if messages_modifier is None:
        model_runnable = agent_model
    elif isinstance(messages_modifier, str):
        _system_message: BaseMessage = SystemMessage(content=messages_modifier)
        model_runnable = (lambda messages: [_system_message] + messages) | agent_model
    elif isinstance(messages_modifier, SystemMessage):
        model_runnable = (lambda messages: [messages_modifier] + messages) | agent_model
    elif isinstance(messages_modifier, (Callable, Runnable)):
        model_runnable = messages_modifier | agent_model
    else:
        raise ValueError(
            f"Got unexpected type for `messages_modifier`: {type(messages_modifier)}"
        )

    if planner_tools is not None:
        planner_model = copy(model)
        if planner_messages_modifier is None:
            planner_model_runnable = planner_model
        elif isinstance(planner_messages_modifier, str):
            p_system_message: BaseMessage = SystemMessage(content=planner_messages_modifier)
            p_system_after: BaseMessage = SystemMessage(content='\nAnalyse the given conversation above.\nAnalysis: ')
            planner_model_runnable = (lambda messages: [p_system_message] + messages + [p_system_after]) | planner_model
        elif isinstance(planner_messages_modifier, SystemMessage):
            planner_model_runnable = (lambda messages: [planner_messages_modifier] + messages) | planner_model
        elif isinstance(planner_messages_modifier, (Callable, Runnable)):
            planner_model_runnable = planner_messages_modifier | planner_model
        else:
            raise ValueError(
                f"Got unexpected type for `planner_messages_modifier`: {type(planner_messages_modifier)}"
            )
    # Define the function that calls the model

    def call_planner(
        state: AgentState,
        config: RunnableConfig,
    ):
        messages = []
        for m in state["messages"][::-1]:
            messages.append(m)
            if len(messages) >= 8:
                if messages[-1].type != "tool":
                    break

        messages = messages[::-1]
        AcceptionList = ['evet', 'tamam', 'onay', 'olur', 'tabi','peki','elbette','eet']
        if any(s in messages[-1].content.lower() for s in AcceptionList) and state["tool_call_message"] is not None:
            return {"messages": [state["tool_call_message"]]}
        else:
            response = planner_model_runnable.invoke(messages, config)
            content = 'Analysis: ' + response.content
            response = AIMessage(content=content,**response.dict(exclude={"content", "type", "name"}), name='Planner')

            return {
                    "messages": [response],
                    "tool_call_message": None,
                }
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
        if any(s in messages[-2].content.lower() for s in AcceptionList) and state["tool_call_message"] is not None:
            pass
        else:
            response = model_runnable.invoke(messages, config)

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
        AcceptionList = ['evet', 'tamam', 'onay', 'olur', 'tabi','peki','elbette','eet']
        if any(s in messages[-2].content.lower() for s in AcceptionList) and state["tool_call_message"] is not None:
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
                call = last_tool_call.artifact.get('call', False)
                if call:
                    state['messages'].append(call)
                    return "tool"
                else:
                    return "continue"
            else:
                return "end"
        else:
            return "end"

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

    def planner_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        # If there is no function call, then we finish
        if last_message.type == "ai":
            if not last_message.tool_calls:
                return "end"
            else:
                if last_message.tool_calls[0]['name'] == "terminate_and_return_to_human":
                    return "end"
                else:
                    return "continue"

    def should_confirm(state: AgentState):
        check = state["tool_call_message"]
        if check:
            return "end"
        else:
            return "continue"

    def confirmation_check(
        state: AgentState,
        config: RunnableConfig,
    ):
        messages = state["messages"]
        last_message = messages[-1]
        # If there is no function call, then we finish
        verification_message = generate_verification_message(last_message)
        if verification_message is not None and state["tool_call_message"] is None:
            last_message.id = str(uuid.uuid4())
            #state["tool_call_message"] = last_message
            state["messages"][-1] = verification_message
            return {'tool_call_message': last_message}
        else:
            return {'tool_call_message': None}
    def dummy_node(
        state: AgentState,
    ):
        pass
    # Define a new graph
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", RunnableLambda(call_planner,name='Planner'))
    #workflow.add_node('p_tools', ToolNode(planner_tools, name='Planner'))

    # Define the two nodes we will cycle between
    workflow.add_node("agent", RunnableLambda(call_model, acall_model))
    workflow.add_node("confirmation", RunnableLambda(confirmation_check))
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("post_tool", RunnableLambda(dummy_node))

    # Set the entrypoint as `agent`
    # This means that this node is the first one called
    workflow.set_entry_point("planner")

    #workflow.add_conditional_edges(
#
    #    "planner",
    #    planner_continue,
#
    #    {
    #        # If `tools`, then we call the tool node.
    #        "continue": "p_tools",
    #        # Otherwise we finish.
    #        "end": END,
    #    },
    #)

    workflow.add_edge("planner", "agent")
    # We now add a conditional edge
    workflow.add_conditional_edges(

        "agent",
        should_continue,

        {
            # If `tools`, then we call the tool node.
            "continue": "confirmation",
            # Otherwise we finish.
            "end": END,
        },
    )

    workflow.add_conditional_edges(

        "confirmation",
        should_confirm,

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
                                       "tool": "confirmation",
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


class Agent:
    def __init__(
            self,
            cart,
            db_client,
            embedding,
            llm_client,
            search_client,
            customer_id,
            customer_email,
            sales_client,
            #stock_service,
            top_n: int= 5,
            debug: bool = False
    ):
        self.cart = cart
        self.db_client = db_client
        self.embedding = embedding
        self.llm_client = llm_client
        self.search_client = search_client
        self.system = LLM_SYSTEM_MESSAGE
        self.customer_id = customer_id
        self.customer_email = customer_email
        self.sales_client = sales_client
        #self.stock_service = stock_service
        self.top_n = top_n
        self.tools = []
        self.tools.append(self.create_structured_tool(self.product_selector,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.retrieve_product_list,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.add_new_product_to_cart,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.get_cart_details,response_in_format='content_and_artifact'))
        #self.tools.append(self.create_structured_tool(self.remove_product_from_cart,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.change_quantity_in_cart,response_in_format='content_and_artifact'))
        #self.tools.append(self.create_structured_tool(self.stock_control,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.get_product_related_campaigns,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.empty_cart,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.create_restock_notification_request,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.ask_when_not_confirmed,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.redirect_to_payment,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.help_human_finding_product,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.out_of_scope,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.tell_your_capabilities,response_in_format='content_and_artifact'))
        self.tools.append(self.create_structured_tool(self.continue_shopping,response_in_format='content_and_artifact'))

        self.planner_tools = []
        self.planner_tools.append(self.create_structured_tool(self.ai_plan, response_in_format = 'content_and_artifact'))
        self.planner_tools.append(self.create_structured_tool(self.terminate_and_return_to_human, response_in_format = 'content_and_artifact'))

        self.agent = create_react_agent(
            model=self.llm_client,
            tools=self.tools,
            checkpointer=self.db_client,
            debug=debug,
            messages_modifier=self.system,
            planner_tools = self.planner_tools,
            planner_messages_modifier = SUPERVISOR_SYSTEM_MESSAGE
            #interrupt_after=["tools"]
        )

    def run(
            self,
            message: str,
            session_id: str
    ):

        config = {"configurable": {"thread_id": session_id, "max_history": 15}}
        inputs = {"messages": [("user", message)]}
        # output = self.agent.stream(inputs, config=config, stream_mode="values")
        output = self.agent.invoke(inputs, config)
        # for i in output['messages']:
        #     print(i)
        # self.add_stream_data_to_collection(self.debug_collection, output, session_id)
        output = self.filtered_return(output)
        # print(output)
        # self.print_stream(output)
        return output, self.cart

    @staticmethod
    def filtered_return(output):
        # if there is a ToolMessage in the messages, return last tool message
        '''
        for i in output["messages"][::-1]:
            if isinstance(i, ToolMessage):
                if i.name in ['retrieve_product_list', 'get_cart_details']:
                    return {'messages': [i]}
                else:
                    break
        '''
        output['messages'] = [output['messages'][-1]]
        return output

    @staticmethod
    def create_structured_tool(callable: Callable,
                               return_direct: bool = False,
                               response_in_format: Literal[
                                   "content",
                                   "content_and_artifact"] = 'content') -> StructuredTool:
        method = callable
        args = {k: v for k, v in method.__annotations__.items() if k not in ["self", "return"]}
        name = method.__name__
        doc = method.__doc__
        func_desc = doc[doc.find("<desc>") + len("<desc>"):doc.find("</desc>")]
        arg_desc = dict()
        for arg in args.keys():
            desc = doc[doc.find(f"{arg}: ") + len(f"{arg}: "):]
            desc = desc[:desc.find("\n")]
            arg_desc[arg] = desc
        arg_fields = dict()
        for k, v in args.items():
            arg_fields[k] = (v, Field(description=arg_desc[k]))

        Model = create_model('Model', **arg_fields)

        tool = StructuredTool.from_function(
            func=method,
            name=name,
            description=func_desc,
            args_schema=Model,
            return_direct=return_direct,
            response_format=response_in_format
        )
        return tool
    
    def ai_plan(self, message: str):
        """
        You use this when creates neccessary directions and explanations for the ai based on user input.
        Args:
            message: detailed explanation of the user input and directions to create respond.
        """
        return message, {'continue': False}
    
    def terminate_and_return_to_human(self):
        """
        You use this to check ai's response is correct for the given human input and you can return it to human.
        """
        return "_END_", {'continue': False}

    def product_selector(self, product_info: str, unit: str, quantity_of_order: int,
                         state: Annotated[dict, InjectedState]) -> Tuple[str, Dict]:
        """
        ai uses this when the human selects specific product from the product list you provided.
        Args:
            product_info: product ID and product name separated by '---'
            quantity_of_order: number of the product human wants to order, buy or add to cart, it must be -1 if user did not state the quantity before. Hint keywords: adet, miktar, birim, koli, paket, kutu
            unit: unit of the product human want to order, it must be None if user did not state the unit. Examples: adet, miktar, birim, koli, paket, kutu Hint: gram is not a unit.
        Returns:
            str: A message to inform human that the product is selected and ask for the quantity.
        """

        product_ID, product_name = product_info.split('---')

        if quantity_of_order == 0 or quantity_of_order == -1:
            return (templates.PRODUCT_SELECTOR.format(product_name=product_name), {'continue': False})
        else:
            id = uuid.uuid4()
            call = AIMessage(content='', additional_kwargs={'tool_calls': [{'id': f'{id}', 'function': {
                'arguments': f'{{"product_info":\"{product_info}\","quantity":{quantity_of_order},"unit":\"{unit}\"}}',
                'name': 'add_new_product_to_cart'}, 'type': 'function'}]}, response_metadata={})
            return ("", {'continue': True, 'call': call})

    '''
    def product_info_to_dict(product_ID: int,
                             product_brand: str,
                             product_name: str,
                             product_specifications: str) -> dict:
        """
        Extract product_ID, product_brand, product_name and product_specifications from user's query to dictionary if
        they exist. if any argument does not exist in the user's query pass it None.

        :params:
        product_ID: at least 5 digit ID of the product.
        product_brand: Brand of the product.
        product_name: Name of the product.
        product_specifications: Weight, size, color, type, etc. of the product.
        """

        dict = {'product_ID': product_ID,
                'product_brand': product_brand,
                'product_name': product_name,
                'product_specifications': product_specifications}
        return dict
    '''

    def retrieve_product_list(self, query: str, quantity_of_order: int, unit: Literal['adet', 'koli',"paket", "None", None, -1],
                              state: Annotated[dict, InjectedState]) -> Tuple[str, Dict]:
        """
        ai MUST always uses this Python function to search the product catalog to find products for the query and return matched list of products to the human.
        Args:
            query: product related information (this information can be product name, brand, type, grammage, weight etc. or combined of this information or just name of product) Examples: acı sos, tat 430 gram domates salçası, Ekin baldo pirinç 5 kg, Nutella 20'li, süt dilimi, 500 kg namet sucuk vb. (Kg, kilogram, gram means weight and must be included in query)
            quantity_of_order: number of the product human want to order, it must be -1 if user did not state the quantity.
            unit: unit of the product human want to order, it must be None if user did not state the unit. unit must be adet, koli or paket. If the unit is not adet, koli or paket, it must be None. Do not confuse about kilo and koli. kilo is not a unit. Kilo means weight.        
        Returns:
            str: A list of the products related to the query.
        """
        llm_message = [("system",EntityExtractorPrompt),("human",query)]
        try:
                
            entity_extractor_output = json.loads(self.llm_client.invoke(llm_message).content)[0]
        except Exception as e:
            entity_extractor_output = {'product_name': "", 'brand_name': "", 'product_weight': "", 'product_feature': ""}
        if entity_extractor_output['product_name'] != "" and entity_extractor_output['brand_name'] != "":
            #print("product name and brand name is not empty")
            if entity_extractor_output['product_weight'] != "":
                query_last = f"product_desc_cleaned:{entity_extractor_output['product_name']}~2 AND brand_desc:{entity_extractor_output['brand_name']}~2 AND product_desc_cleaned:{entity_extractor_output['product_weight']}~1"
            else:
                query_last = f"product_desc_cleaned:{entity_extractor_output['product_name']}~1 AND brand_desc:{entity_extractor_output['brand_name']}~1"
        elif entity_extractor_output['brand_name'] == "" and entity_extractor_output['product_name'] == "":
            query_last = f"product_desc_cleaned:{query}~1"
        elif entity_extractor_output['brand_name'] == "" and entity_extractor_output['product_name'] != "":
            query_last = f"product_desc_cleaned:{entity_extractor_output['product_name']}~2"
            
        else:
            query_last = f"product_desc_cleaned:{query}~"
        embedding = self.embedding.embed_query(query)
        vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=self.top_n, fields="myHnsw")

        result = self.search_client.search(
            search_text=query_last,
            vector_queries=[vector_query],
            query_type="full",
            semantic_query=query,
            semantic_configuration_name="semanticconfig",
            top=self.top_n
        )
        result_search = []
        for i in result:
            result_search.append(i)
        result = result_search
        result2 = [record for record in result if record.get("@search.reranker_score") >= 2.0]
        result = result2
        if len(result) == 0:
            return "Aradığınız ürün bulunamamıştır. Başka ürün aramak ister misiniz?", {'continue': False}




        result_to_artifact = [(record['product_code'], linenumber+1) for record, linenumber in zip(result, range(len(result)))]
        if result[0]['@search.reranker_score'] < 2.0 or len(result) == 0:
            return templates.RETRIEVE_PRODUCT_LIST_NO_MATCH, {'continue': False, 'voice_name': 'not_found', "sub_condition": "no_match", "mapped_output": ""}

        if len(result)==1:
            if (quantity_of_order == 0 or quantity_of_order == -1):
                if unit is None or unit == "None" or str(unit) == "-1":
                    return templates.RETRIEVE_PRODUCT_LIST_MATCH.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc']), {'continue': False, "sub_condition": "direct_match_wout_quantity", "product_id": result[0]['product_code'], "quantity": quantity_of_order, "unit": "adet","mapped_output": templates.RETRIEVE_PRODUCT_LIST_MATCH.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc'])}
                else:
                    return templates.RETRIEVE_PRODUCT_LIST_MATCH_WITH_UNIT.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc'], unit=unit), {'continue': False, "sub_condition": "direct_match_wout_quantity", "product_id": result[0]['product_code'], "quantity": quantity_of_order, "unit": unit, "mapped_output": templates.RETRIEVE_PRODUCT_LIST_MATCH_WITH_UNIT.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc'], unit=unit)}
                # return f"{result[0]['urunkod']} --- {result[0]['uruntanim']} isimli ürünü seçtiniz. Kaç adet eklemek istediğinizi belirtir misiniz?", {'continue': False}
            else:
                if unit is None or unit == "None" or str(unit) == "-1":
                    return templates.RETRIEVE_PRODUCT_LIST_MATCH_DIRECTED.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc'], quantity_of_order=quantity_of_order), {'continue': True, "sub_condition": "direct_match_with_quantity", "product_id": result[0]['product_code'], "quantity": quantity_of_order, "unit": "adet","mapped_output": templates.RETRIEVE_PRODUCT_LIST_MATCH_DIRECTED.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc'], quantity_of_order=quantity_of_order)}
                else:
                    return templates.RETRIEVE_PRODUCT_LIST_MATCH_WITH_UNIT_DIRECTED.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc'], quantity_of_order=quantity_of_order, unit=unit), {'continue': True, "sub_condition": "direct_match_with_quantity", "product_id": result[0]['product_code'], "quantity": quantity_of_order, "unit": unit,"mapped_output": templates.RETRIEVE_PRODUCT_LIST_MATCH_WITH_UNIT_DIRECTED.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc'], quantity_of_order=quantity_of_order, unit=unit)}
        elif result[0]['@search.reranker_score'] - result[1]['@search.reranker_score'] > 0.4:

            if (quantity_of_order == 0 or quantity_of_order == -1):
                if unit is None or unit == "None" or str(unit) == "-1":
                    return templates.RETRIEVE_PRODUCT_LIST_MATCH.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc']), {'continue': False, "sub_condition": "direct_match_wout_quantity", "product_id": result[0]['product_code'], "quantity": quantity_of_order, "unit": "adet","mapped_output": templates.RETRIEVE_PRODUCT_LIST_MATCH.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc'])}
                else:
                    return templates.RETRIEVE_PRODUCT_LIST_MATCH_WITH_UNIT.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc'], unit=unit), {'continue': False, "sub_condition": "direct_match_wout_quantity", "product_id": result[0]['product_code'], "quantity": quantity_of_order, "unit": unit, "mapped_output": templates.RETRIEVE_PRODUCT_LIST_MATCH_WITH_UNIT.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc'], unit=unit)}
                # return f"{result[0]['urunkod']} --- {result[0]['uruntanim']} isimli ürünü seçtiniz. Kaç adet eklemek istediğinizi belirtir misiniz?", {'continue': False}
            else:
                if unit is None or unit == "None" or str(unit) == "-1":
                    return templates.RETRIEVE_PRODUCT_LIST_MATCH_DIRECTED.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc'], quantity_of_order=quantity_of_order), {'continue': True, "sub_condition": "direct_match_with_quantity", "product_id": result[0]['product_code'], "quantity": quantity_of_order, "unit": "adet","mapped_output": templates.RETRIEVE_PRODUCT_LIST_MATCH_DIRECTED.format(product_code=result[0]['product_code'], product_info=result[0]['product_code'], quantity_of_order=quantity_of_order)}
                else:
                    return templates.RETRIEVE_PRODUCT_LIST_MATCH_WITH_UNIT_DIRECTED.format(product_code=result[0]['product_code'], product_info=result[0]['product_desc'], quantity_of_order=quantity_of_order, unit=unit), {'continue': True, "sub_condition": "direct_match_with_quantity", "product_id": result[0]['product_code'], "quantity": quantity_of_order, "unit": unit,"mapped_output": templates.RETRIEVE_PRODUCT_LIST_MATCH_WITH_UNIT_DIRECTED.format(product_code=result[0]['product_code'], product_info=result[0]['product_code'], quantity_of_order=quantity_of_order, unit=unit)}
            
        
        else:
            if quantity_of_order == 0 or quantity_of_order == -1:
                product_list = 'Eşleşen ürünler:\n'
                product_list_mapped = 'Eşleşen ürünler:\n'
                for idx, pr_i in enumerate(result):
                    product_list += f"{idx + 1}. {pr_i['product_code']}---{pr_i['product_desc']}\n"
                    product_list_mapped += f"{idx + 1}. {pr_i['product_code']}---{pr_i['product_desc']}\n"
                product_list += templates.RETRIEVE_PRODUCT_LIST
                product_list_mapped += templates.RETRIEVE_PRODUCT_LIST
                return (product_list, {'continue': False, "product_suggestion": result_to_artifact, "sub_condition": "multiple_match", "mapped_output": product_list_mapped})
            elif quantity_of_order > 0 and (unit is not None and unit != "None" and unit != -1):
                product_list = 'Eşleşen ürünler:\n'
                product_list_mapped = 'Eşleşen ürünler:\n'
                for idx, pr_i in enumerate(result):
                    product_list += f"{idx + 1}. {pr_i['product_code']}---{pr_i['product_desc']}\n"
                    product_list_mapped += f"{idx + 1}. {pr_i['product_code']}---{pr_i['product_desc']}\n"
                product_list += templates.RETRIEVE_PRODUCT_LIST_WITH_UNIT.format(quantity_of_order=quantity_of_order, unit=unit)
                product_list_mapped += templates.RETRIEVE_PRODUCT_LIST_WITH_UNIT.format(quantity_of_order=quantity_of_order, unit=unit)
                return (product_list, {'continue': False, "product_suggestion": result_to_artifact, "sub_condition": "multiple_match", "mapped_output": product_list_mapped})
            else:
                product_list = 'Eşleşen ürünler:\n'
                product_list_mapped = 'Eşleşen ürünler:\n'
                for idx, pr_i in enumerate(result):
                    product_list += f"{idx + 1}. {pr_i['product_code']}---{pr_i['uruntanim']}\n"
                    product_list_mapped += f"{idx + 1}. {pr_i['product_code']}---{pr_i['product_desc']}\n"
                product_list += templates.RETRIEVE_PRODUCT_LIST_WITHOUT_UNIT.format(quantity_of_order=quantity_of_order)
                product_list_mapped += templates.RETRIEVE_PRODUCT_LIST_WITHOUT_UNIT.format(quantity_of_order=quantity_of_order)
                return (product_list, {'continue': False, "product_suggestion": result_to_artifact, "sub_condition": "multiple_match", "mapped_output": product_list_mapped})

    def add_new_product_to_cart(self, product_info: str, quantity: int, unit: str,
                                state: Annotated[dict, InjectedState]) -> Tuple[str, Dict]:
        """
        ai uses this when the human wants to add a new product to the cart that does not exists in the cart with a KNOWN quantity.

        Args:
            product_info: product ID and product name separated by '---'.
            quantity: number of the product user want to add to cart.
            unit: unit of the product human want to order, it must be None if user did not state the unit. Examples: adet, miktar, birim, koli, paket, kutu
        Returns:
            str: A message to inform human that the product is added to the cart.
        """

        product_ID, product_name = product_info.split('---')

        stock_message, artifact = self.stock_control(product_ID, quantity)

        if artifact['condition'] == 1:
            self.cart.append({'no': len(self.cart) + 1, 'product': product_name, 'quantity': quantity})
            return templates.ADD_NEW_PRODUCT_TO_CART, {'continue': False, "product_id": product_ID, "quantity": quantity, "unit": unit,"condition": 1, 'voice_name': 'add_to_cart'}
        elif artifact['condition'] == 2:
            return stock_message, {'continue': False, "product_id": product_ID, "quantity": quantity, "unit": unit, "condition": 2}
        else:
            return stock_message, {'continue': False, "product_id": product_ID, "quantity": quantity, "unit": unit, "condition": 3}

    def get_product_related_campaigns(self, product_info: str) -> Tuple[str, Dict]:
        """
        ai uses this when the human wants to see, search any campaign or discounts related to their query.
        keywords: kampanya, şu indirimli ürün var mı?, diskonto, promosyon, promosyonlu ürün.

        Args:
            product_info: product related information given by human.
        Returns:
            str: A list of the campaigns related to the product.
        """
        answer = "Size özel 2500 TL üzeri %25 kampanya bulunmaktadır."
        return answer, {'continue': False}

    def get_cart_details(self) -> Tuple[str, Dict]:
        """
        ai uses it to get current state of the customer cart for making any cart related process on it.

        Returns:
            str: A list of the products in the cart.

        """
        output = "Mevcut Sepet:\nItem Key, Item Name, Item Quantity, Item Unit"
        for i in self.cart:
            #output += f"{i['no']},{i['product']},{i['quantity']}\n"
            output += f"{i['ItemKey']}, {i['ItemName']}, {i['ItemQuantity']}, {i['ItemUnit']}"

        output = output + 'add_new_product_to_cart, change_quantity_in_cart yada empty_cart toollarında ilgili olanı çağır.\n'
        output = output + ('Eğer sepette olmayan yeni bir ürün ile ilgiliyse ise add_new_product_to_cart'
                           'Eğer sepette bulunan bir ürün ilgili ise change_quantity_in_cart '
                           'Eğer sepeti tamamen boşaltmakla ilgili ise empty_cart kullan.\n')

        return output, {'continue': True}

    def change_quantity_in_cart(self, product_order: int, quantity: int) -> Tuple[str, Dict]:
        """
        ai MUST use it to change quantity of the any desired product in the cart or add more or decrease of the same product in the cart.
        add or remove change of quantity to existed quantity in the cart, if quantity is 0, remove the product from the cart.

        Args:
            product_order: number indicates position of the selected product in the cart. between 1 and len(cart)
            quantity: new quantity of the product (after addition or subtraction).

        Returns:
            str: A message to inform human that their cart is updated.
        """
        if len(self.cart) == 0:
            return templates.CHANGE_QUANTITY_IN_CART_EMPTY_CART, {'continue': False, "sub_condition": "no_product",'voice_name': 'empty_cart'}

        current_quantity = self.cart[product_order - 1]['ItemQuantity']
        ItemKey = self.cart[product_order - 1]['ItemKey']
        ItemUnit = self.cart[product_order - 1]['ItemUnit']
        if current_quantity == quantity:
            return templates.CHANGE_QUANTITY_IN_CART_SAME_QUANTITY, {'continue': False, "sub_condition": "same_quantity", "voice_name":"item_exists"}
        if quantity == 0:
            ItemKey = self.cart[product_order - 1]['ItemKey']
            ItemUnit = self.cart[product_order - 1]['ItemUnit']
            self.cart.pop(product_order - 1)
            return templates.CHANGE_QUANTITY_IN_CART_REMOVE, {'continue': False, "name": "remove_product_from_cart", "product_order": product_order, "product_id": ItemKey, "unit": ItemUnit,"sub_condition": "remove_all", "voice_name": "remove_item"}
        if current_quantity < quantity:
            check_quantity = quantity - current_quantity
            stock_message, artifact = self.stock_control(self.cart[product_order - 1]['ItemKey'], check_quantity)
            if artifact['condition'] == 1:
                self.cart[product_order - 1]['ItemQuantity'] = quantity
                return templates.CHANGE_QUANTITY_IN_CART_UPDATE, {'continue': False, "sub_condition": "reduce_success", "product_id": ItemKey, "unit": ItemUnit, "quantity": quantity, "voice_name": "cart_updated"}
            else:
                return stock_message, {'continue': False, "sub_condition": "reduce_fail"}
        else:
            self.cart[product_order - 1]['ItemQuantity'] = quantity
            return templates.CHANGE_QUANTITY_IN_CART_UPDATE, {'continue': False, "sub_condition": "reduce_success", "product_id": ItemKey, "unit": ItemUnit, "quantity": quantity,"voice_name": "cart_updated"}

    def empty_cart(self) -> Tuple[str, Dict]:
        """
        ai must use it when you get confirmation from human about empty, cleaning every element in the cart.

        Returns:
            str: A message to inform human that their cart is empty now.
        """
        self.cart = []

        return templates.EMPTY_CART, {'continue': False, "voice_name":"cart_emptied"}

    def stock_control(self, product_ID: str, quantity: int) -> Tuple[str, Dict]:
        """
        ai MUST use it to check the stock of the product before adding any product to cart.

        Args:
            product_ID: ID number of the product.
            quantity: number of the product.
        Returns:
            str: A message to inform human about the stock of the product or continue to call new tool.
        """
        #stock amount will be generated randomly between 0 and 10
        stock_amount = random.randint(0, 10)

        if quantity <= stock_amount:
            return templates.STOCK_CONTROL_POSITIVE, {"condition": 1, 'continue': True}
        elif stock_amount == 0:
            return templates.STOCK_CONTROL_NEGATIVE, {"condition": 2, 'continue': False, "voice_name":"out_of_stock"}
        else:
            return templates.STOCK_CONTROL_CONDITIONAL.format(stock_amount=stock_amount), {"condition": 3, 'continue': False}

    def create_restock_notification_request(self, product_ID: str, quantity: int) -> Tuple[str, Dict]:
        """
        ai uses it to create a notification request to inform human when the product is restocked.

        Args:
            product_ID: ID number of the product.
            quantity: number of the product.
        Returns:
            str: A message to inform human that their request is taken and they will be informed when the product is restocked.
        """
        return templates.CREATE_STOCK_NOTIFICATION_REQUEST, {'continue': False, "voice_name": "request_received", "product_id": product_ID, "quantity": quantity}

    def ask_when_not_confirmed(self) -> Tuple[str, Dict]:
        """
        ai must use this tool when human does not approve when ai ask for any confirmation.

        Returns:
            str: A message to ask human for their intention.
        """
        return templates.ASK_WHEN_NOT_CONFIRMED, {'continue': False, 'voice_name': 'action_not_confirmed'}

    def continue_shopping(self) -> Tuple[str, Dict]:
        """
        ai must use this tool when human wants to continue shopping. example: alışverişe devam et.
        """

        return templates.CONTINUE_SHOPPING, {'continue': False,"voice_name": "help_needed"}

    def tell_your_capabilities(self, type: Literal['name', 'functions']) -> Tuple[str, Dict]:
        """
        ai must use this tool when human wants to know about ai's functionalities, topics that ai can help or ai's name.

        Args:
            type: type of the information human wants to get from ai.
        Returns:
            str: A message to ask human for their intention.
        """
        if type == 'name':
            return templates.TELL_YOUR_CAPABILITIES_NAME, {'continue': False, "voice_name": "introduce_yourself"}
        else:
            return templates.TELL_YOUR_CAPABILITIES_OTHER, {'continue': False, "voice_name":"help_needed"}

    def redirect_to_payment(self) -> Tuple[str, Dict]:
        """
        ai must use this tool when human wants to conclude shopping and go to payment page.

        Returns:
            str: A message to inform human that they will be redirected to payment page.
        """
        return templates.REDIRECT_TO_PAYMENT, {'continue': False, "voice_name":"direct_to_payment"}

    def help_human_finding_product(self) -> Tuple[str, Dict]:
        """
        ai must use this tool when human says that they cannot find the product they are looking for or they want different product from the list.

        Returns:
            str: A message to inform human that you can not understand their query and ask for repeat.
        """
        return templates.HELP_HUMAN_FINDING_PRODUCT, {'continue': False, "voice_name":"not_understood"}

    def out_of_scope(self) -> Tuple[str, Dict]:
        """
        ai uses this tool when the human query is out of the scope of the agent.

        Returns:
            str: A message to inform user that you cannot help with this task ask for any other task.
        """
        return templates.OUT_OF_SCOPE, {'continue': False}