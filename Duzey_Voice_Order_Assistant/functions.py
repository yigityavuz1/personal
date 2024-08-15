import os

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from typing import Literal
from azure.search.documents.models import VectorizedQuery
from create_agent import InjectedState, Annotated
import glob
import pprint
from typing import Dict, Tuple, List
import random
from langchain.document_loaders import TextLoader
from langchain_openai import AzureOpenAIEmbeddings
from langchain.tools import StructuredTool
from langchain.pydantic_v1 import Field, create_model
from typing import Callable
from create_agent import create_react_agent
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import AIMessage, ToolMessage
import os
from langchain.globals import set_debug
from mongo_db_memory import MongoDBSaver, MongoClient
from yaml import safe_load
import requests
import pymongo
with open('config.yaml',mode='r') as f:
    config = safe_load(f)

import uuid

set_debug(True)

MONGO_URI = "mongodb://duzey-voiceorder-mongo:ziLtSlQOUm8DT25N28KglTUyYzaHgDuzO4Pd29sffpXvOtKzxk4IIvK27V1OnjGodiPYj1HTz3TYACDbC6MSzA==@duzey-voiceorder-mongo.mongo.cosmos.azure.com:10255/?ssl=true&retrywrites=false&replicaSet=globaldb&maxIdleTimeMS=120000&appName=@duzey-voiceorder-mongo@"
#MONGO_URI = "mongodb://localhost:27017"
os.environ["OPENAI_API_VERSION"] = "2024-02-01"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://voiceorder-openai.openai.azure.com/"
os.environ["AZURE_OPENAI_API_KEY"] = "f702f663e199450a9c1be25e24d5b49a"


class AgentTest:
    def __init__(self, debug: bool = False):
        self.system = '''You are a shopping ai called Asista. 
You MUST use given tools to interact with human. After calling appropriate tool for human query, you have to get response from the human.
You should always answer in the same language as the human asked the question.
You can not call multiple tools at the same time.
WHEN human asks, wants to buy or add to cart, search for the products, First you MUST use the `retrieve_product_list` tool to provide list of products for selection.
WHEN human selects a product from the list, you MUST ALWAYS use the `product_selector` tool and pass quantity if it is given before.
WHEN human wants to add selected product to cart, you MUST ALWAYS use the `add_new_product_to_cart` tool to add it to cart.
You MUST Always call `get_cart_details` tool to see current status of cart BEFORE doing any change on the cart.
You MUST Always check list of products before adding it to cart. If desired product is not on the previously given list, provide a new list by calling `retrieve_product_list`.
Always use tools properly to complete the given tasks.
WHEN you ask for confirmation, IF human doesn't approve, use `ask_when_not_confirmed` tool to get their intention.
If human ask anything is NOT related with your scope, functionalities, your name, greetings or thanking you call `out_of_scope` tool and DO NOT say out_of_scope directly.
IF you are not certain about parameters of the tools, you MUST ask for clarification from the human.
ai: Merhaba, Ben Asista! Size nasıl yardımcı olabilirim? İstediğiniz ürünün adını ve almak istediğiniz miktarı söyleyebilirsiniz.'''
        self.llm_deployment = "gpt35-0125"
        self.embedding_deployment = "text-embedding-canada"

        self.init_ai_search()
        self.init_mongo()
        self.setup(debug=debug)
        self.cart = []
        self.config = config


    def init_ai_search(self):
        self.ai_serch_config = {'ai_search_credentials':
                                    {'api_key': "4sBN1ZJSy3WB2xgDAzqHDZ5VmsxaElPYr2XOpuXe6kAzSeACcSvo",
                                     'endpoint': "https://voiceorder-ai-search-new.search.windows.net",
                                     'index_name': "products"}
                                }

        self.azure_credential = AzureKeyCredential(self.ai_serch_config['ai_search_credentials']['api_key'])

        self.index_client = SearchClient(self.ai_serch_config['ai_search_credentials']['endpoint'],
                                         self.ai_serch_config['ai_search_credentials']['index_name'],
                                         self.azure_credential)
    def init_mongo(self):
        self.mongo_client = pymongo.MongoClient(MONGO_URI)
        self.sales_db_cl = self.mongo_client["voice_order_assistant"]
        self.sales_coll_cl = self.sales_db_cl["sales"]

    def setup(self, debug: bool = False):
        self.llm = AzureChatOpenAI(azure_deployment=self.llm_deployment, temperature=0.01)
        self.embedding = AzureOpenAIEmbeddings(azure_endpoint='https://voiceorder-openai.openai.azure.com/',
                                               openai_api_key='f702f663e199450a9c1be25e24d5b49a',
                                               deployment='text-embedding-canada')

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

        # MongoClient(MONGO_URI).drop_database("checkpoints_db")
        self.client = MongoClient(MONGO_URI)
        self.memory = MongoDBSaver(self.client, "checkpoints_db", "checkpoints_collection")
        self.debug_db = self.client["debug_db"]
        self.debug_collection = self.debug_db["debug_collection"]

        self.agent = create_react_agent(self.llm,
                                        tools=self.tools,
                                        checkpointer=self.memory,
                                        debug=debug,
                                        messages_modifier=self.system,
                                        #interrupt_after=["tools"]
                                        )

    def run(self, message: str, session_id: str, cart: list, user_id:str, usermail:str):

        self.cart = cart
        config = {"configurable": {"thread_id": session_id, "max_history": 15}}
        inputs = {"messages": [("user", message)]}
        # output = self.agent.stream(inputs, config=config, stream_mode="values")
        output = self.agent.invoke(inputs, config)
        for i in output['messages']:
            print(i)
        # self.add_stream_data_to_collection(self.debug_collection, output, session_id)
        output = self.filtered_return(output)
        self.user_id = user_id
        self.usermail = usermail
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

    def product_selector(self, product_info: str,unit:str, quantity_of_order: int) -> Tuple[str, Dict]:
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
            return (f"{product_name} isimli ürünü seçtiniz. Sepete kaç adet eklemek istediğinizi belirtir misiniz?", {'continue': False})
        else:
            return (f"{product_name} isimli üründen {quantity_of_order} adet seçtiniz. doğrudan sepete ekle.", {'continue': True})

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

    def retrieve_product_list(self, query: str, quantity_of_order: int,unit :Literal['adet','koli', 'None'], state: Annotated[dict, InjectedState]) -> Tuple[str, Dict]:
        """
        ai MUST always uses this Python function to search the product catalog to find products for the query and return matched list of products to the human.
        Args:
            query: product related information (this information can be product name, brand, type, grammage, etc. or combined of this information) Example: tat 430 gram domates salçası
            quantity_of_order: number of the product human want to order, it must be -1 if user did not state the quantity. Hint keywords: adet, miktar, birim, koli, paket, kutu
            unit: unit of the product human want to order, it must be None if user did not state the unit. unit must be adet or koli.
        Returns:
            str: A list of the products related to the query.
        """
        print(quantity_of_order)
        embedding = self.embedding.embed_query(query)
        vector_query = VectorizedQuery(vector=embedding, k_nearest_neighbors=5, fields="myHnsw")

        result = self.index_client.search(
            search_text=query,
            vector_queries=[vector_query],
            query_type="semantic",
            semantic_configuration_name="semanticconfig",
            top=5
        )
        result_search = []
        for i in result:
            result_search.append(i)
        result = result_search

        product_list_withID = [{"MusteriKod": self.user_id, "UrunKod": product['urunkod']} for product in result]
        mongo_search_query = {"$or": product_list_withID}
        mongo_search = self.sales_coll_cl.find(mongo_search_query)
        print(result)
        if result[0]['@search.reranker_score'] - result[1]['@search.reranker_score'] > 0.4:
            if (quantity_of_order == 0 or quantity_of_order == -1):
                if unit is None:
                    return f"{result[0]['urunkod']} --- {result[0]['uruntanim']} isimli ürünü seçtiniz. Kaç adet eklemek istediğinizi belirtir misiniz?", {'continue': False}
                else:
                    return f"{result[0]['urunkod']} --- {result[0]['uruntanim']} isimli üründen sepetinize kaç {unit} eklemek istersiniz?", {'continue': False}
                #return f"{result[0]['urunkod']} --- {result[0]['uruntanim']} isimli ürünü seçtiniz. Kaç adet eklemek istediğinizi belirtir misiniz?", {'continue': False}
            else:
                if unit is None:
                    return f"{result[0]['urunkod']} --- {result[0]['uruntanim']} isimli üründen {quantity_of_order} adet seçtiniz. doğrudan sepete ekle (add_new_product_to_cart).", {'continue': True}
                else:
                    return f"{result[0]['urunkod']} --- {result[0]['uruntanim']} isimli üründen {quantity_of_order} {unit} seçtiniz. doğrudan sepete ekle. (add_new_product_to_cart)", {'continue': True}
        else:
            if quantity_of_order == 0 or quantity_of_order == -1:
                product_list = 'Eşleşen ürünler:\n'
                for idx, pr_i in enumerate(result):
                    product_list += f"{idx + 1}. {pr_i['urunkod']}---{pr_i['uruntanim']}\n"
                product_list += f"Listeden sepetinize eklemek istediğiniz ürünü ve miktarını belirtin. Eğer başka bir ürün aramak isterseniz, lütfen belirtin."

                return (product_list, {'continue': False})
            elif quantity_of_order > 0 and unit is not None:
                product_list = 'Eşleşen ürünler:\n'
                for idx, pr_i in enumerate(result):
                    product_list += f"{idx + 1}. {pr_i['urunkod']}---{pr_i['uruntanim']}\n"
                product_list += f"Hangi ürünü seçmek istediğinizi belirtirseniz, sepetinize {quantity_of_order} {unit} ekleyebilirim."
                return (product_list , {'continue': False})
            else:
                product_list = 'Eşleşen ürünler:\n'
                for idx, pr_i in enumerate(result):
                    product_list += f"{idx + 1}. {pr_i['urunkod']}---{pr_i['uruntanim']}\n"
                product_list += f"Hangi ürünü seçmek istediğinizi belirtirseniz, sepetinize {quantity_of_order} adet ekleyebilirim."
                return (product_list , {'continue': False})

    def add_new_product_to_cart(self, product_info: str, quantity: int,unit:str, state: Annotated[dict, InjectedState]) -> Tuple[str, Dict]:
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

        stock_message, artifact= self.stock_control(product_ID, quantity)

        if artifact['condition'] == 1:
            self.cart.append({'no': len(self.cart) + 1, 'product': product_name, 'quantity': quantity})
            return f"Ürününüz başarıyla sepete eklendi. Alışverişe devam edebilir veya ödeme adımına geçebilirsiniz.", {'continue': False}
        elif artifact['condition'] == 2:
            return stock_message, {'continue': False}
        else:
            return stock_message, {'continue': False}

    def get_product_related_campaigns(self, product_info: str) -> str:
        """
        ai uses this when the human wants to see, search any campaign or discounts related to their query.
        keywords: kampanya, şu indirimli ürün var mı?, diskonto, promosyon, promosyonlu ürün.

        Args:
            product_info: product related information given by human.
        Returns:
            str: A list of the campaigns related to the product.
        """

        return f"{product_info} ile ilgili COR sistemine gidip USERID için kampanyaları aldığımı varsay. Başka hangi konuda yardımcı olabilirim.", {'continue': False}

    def get_cart_details(self) -> Tuple[str, Dict]:
        """
        ai uses it to get current state of the customer cart for making any cart related process on it.

        Returns:
            str: A list of the products in the cart.

        """
        output = "Mevcut Sepet:\nNo,Product_info,Quantity\n"
        for i in self.cart:
            output += f"{i['no']},{i['product']},{i['quantity']}\n"

        output = output + 'add_new_product_to_cart, change_quantity_in_cart yada empty_cart toollarında ilgili olanı çağır.\n'
        output = output + ('Eğer sepette olmayan yeni bir ürün ile ilgiliyse ise add_new_product_to_cart'
                           'Eğer sepette bulunan bir ürün ilgili ise change_quantity_in_cart '
                           'Eğer sepeti tamamen boşaltmakla ilgili ise empty_cart kullan.\n')



        return output, {'continue': True}

    def remove_product_from_cart(self, product_order: int) -> str:
        """
        ai uses it to remove any given product from the cart.

        Args:
            product_order: number indicates position of the selected product in the cart. between 1 and len(cart)
        Returns:
            str: A message to inform human that selected product was removed from the cart.
        """

        self.cart.pop(product_order - 1)
        return f'Seçtiğiniz ürün sepetten çıkarıldı.', {'continue': False}

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
            return 'Üzgünüm sepetinizde hiç ürün bulunmamaktadır. Alışverişe devam etmek ister misiniz?', {'continue': False}

        current_quantity = self.cart[product_order - 1]['quantity']

        if current_quantity == quantity:
            return 'Bu üründen zaten bu kadar sepetinizde var. Başka bir işlem yapmak ister misiniz?', {'continue': False}
        if quantity == 0:
            self.cart.pop(product_order - 1)
            return f'Seçtiğiniz ürün sepetten çıkarıldı. Alışverişe devam etmek ister misiniz?', {'continue': False}
        if current_quantity < quantity:
            check_quantity = quantity - current_quantity
            stock_message, artifact = self.stock_control(self.cart[product_order - 1]['product'], check_quantity)
            if artifact['condition'] == 1:
                self.cart[product_order - 1]['quantity'] = quantity
                return f'Sepetiniz güncellendi. Alışverişe devam etmek ister misiniz?', {'continue': False}
            else:
                return stock_message, {'continue': False}
        else:
            self.cart[product_order - 1]['quantity'] = quantity
            return f'Sepetiniz güncellendi. Alışverişe devam etmek ister misiniz?', {'continue': False}

    def empty_cart(self) -> Tuple[str, Dict]:
        """
        ai must use it when you get confirmation from human about empty, cleaning every element in the cart.

        Returns:
            str: A message to inform human that their cart is empty now.
        """
        self.cart = []

        return f'Sepetiniz boşaltıldı. Alışverişe devam etmek ister misiniz?', {'continue': False}

    def stock_control(self, product_ID: str, quantity: int) -> Tuple[str, Dict]:
        """
        ai MUST use it to check the stock of the product before adding any product to cart.

        Args:
            product_ID: ID number of the product.
            quantity: number of the product.
        Returns:
            str: A message to inform human about the stock of the product or continue to call new tool.
        """
        auth_url = self.config["stock_control"]["authorization_url"]
        body = {
            "username": self.config["stock_control"]["user"],
            "password": self.config["stock_control"]["password"],
            "client_id": self.config["stock_control"]["client_id"],
            "client_secret": self.config["stock_control"]["client_secret"]
        }

        response_token = requests.post(auth_url,data=body)

        auth_token = response_token.text
        headers = {
            'Authorization': f'Bearer {auth_token}'
        }

        url = self.config["stock_control"]["url"]
        url = url + f'duzey/users/{self.usermail}/stock?product={product_ID}'
        response = requests.get(url, headers=headers)
        response = response.json()
        stock_amount = response['avaliable']

        if quantity <= stock_amount:
            return 'Bu ürün stoklarımızda mevcut. add_product_to_cart ile ürünü sepete ekle', {"condition":1,'continue': True}
        elif stock_amount == 0:
            return "Bu ürün şu anda stokta yok. Gelince sizi bilgilendirmemi ister misiniz?", {"condition":2,'continue': False}
        else:
            return f"Bu ürün stoklarımızda sınırlıdır; bu üründen en fazla {stock_amount} adet sepete ekleyebilirim. Bu miktarda eklemek ister misiniz?", {"condition":3,'continue': False}

    def create_restock_notification_request(self, product_ID: str, quantity: int) -> Tuple[str, Dict]:
        """
        ai uses it to create a notification request to inform human when the product is restocked.

        Args:
            product_ID: ID number of the product.
            quantity: number of the product.
        Returns:
            str: A message to inform human that their request is taken and they will be informed when the product is restocked.
        """
        return f"Talebiniz alındı, ürün geldiğinde bilgilendirileceksiniz.", {'continue': False}

    def ask_when_not_confirmed(self) -> Tuple[str, Dict]:
        """
        ai must use this tool when human does not approve when ai ask for any confirmation.

        Returns:
            str: A message to ask human for their intention.
        """
        return "İşlemi onaylamadınız. Yeni bir ürün arayabilir veya ödeme adımına geçebilirsiniz.", {'continue': False}
    
    def continue_shopping(self) -> Tuple[str, Dict]:
        """
        ai must use this tool when human wants to continue shopping.
        """

        return "Size ürün listeleme, satın alma ve kampanyalara ulaşmada, sepet işlemlerinde, ödeme adımına geçmede yardımcı olabilirim. Lütfen yapmak istediğiniz işlemi söyleyin." , {'continue': False}

    def tell_your_capabilities(self, type: Literal['name','functions']) -> Tuple[str, Dict]:
        """
        ai must use this tool when human wants to know about ai's functionalities, topics that ai can help or ai's name.

        Args:
            type: type of the information human wants to get from ai.
        Returns:
            str: A message to ask human for their intention.
        """
        if type == 'name':
            return "Benim adım Asista. Size nasıl yardımcı olabilirim?", {'continue': False}
        else:
            return "Size ürün listeleme, satın alma ve kampanyalara ulaşmada, sepet işlemlerinde, ödeme adımına geçmede yardımcı olabilirim. Lütfen yapmak istediğiniz işlemi söyleyin.", {'continue': False}
    def redirect_to_payment(self) -> Tuple[str, Dict]:
        """
        ai must use this tool when human wants to conclude shopping and go to payment page.

        Returns:
            str: A message to inform human that they will be redirected to payment page.
        """
        return "Ödeme sayfasına yönlendiriyorum. Görüşmek Üzere!", {'continue': False}

    def help_human_finding_product(self) -> Tuple[str, Dict]:
        """
        ai must use this tool when human has trouble with finding desired product on the given lists to tell them to enlarge, enrich their search query by repeating.,


        Returns:
            str: A message to inform human that you can not understand their query and ask for repeat.
        """
        return "Aradığınız ürünü bulmada zorluk yaşıyorsanız. Lütfen farklı şekilde zenginleştirerek tekrar eder misiniz?", {'continue': False}

    def out_of_scope(self) -> Tuple[str, Dict]:
        """
        ai uses this tool when the human query is out of the scope of the agent.

        Returns:
            str: A message to inform user that you cannot help with this task ask for any other task.
        """
        return "Üzgünüm, bu konuda yardımcı olamam. \
        İstediğiniz ürünün adını ve almak istediğiniz miktarı söyleyebilirsiniz, sepetinizle ilgili işlem yapabilir, \
        ürünlerle ilgili kampanyalara ulaşabilir veya ödeme adımına geçebilirsiniz.", {'continue': False}

    @staticmethod
    def print_stream(stream):
        for s in stream:
            message = s["messages"][-1]
            if isinstance(message, tuple):
                print(message)
            else:
                message.pretty_print()

    @staticmethod
    def add_stream_data_to_collection(collection, stream, session_id):
        def merge(dict1, dict2):
            res = {**dict1, **dict2}
            return res

        for s in stream:
            session_id_dict = {"session_id": session_id}
            message_dict = dict(s["messages"][-1])
            collection.insert_one(merge(session_id_dict, message_dict))