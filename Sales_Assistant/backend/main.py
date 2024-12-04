from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
import os
from pymongo import MongoClient
from yaml import safe_load
from configparser import ConfigParser
from agent.agent import Agent
from agent.checkpointer import MongoDBSaver
from agent.schemas import RequestModel, SimpleDataModel
from agent.helper_functions import output_creator
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


app = FastAPI()
vault_url = "https://kv-sales-assistant-dev.vault.azure.net/"
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=vault_url, credential=credential)
 
# Key Vault üzerinden OpenAI ve AI Search için anahtarları al
openai_key = secret_client.get_secret("OPENAI-KEY").value
ai_search_key = secret_client.get_secret("AI-SEARCH-ADMIN-KEY").value
mongo_conn_string = secret_client.get_secret("MONGO-CONN-STRING").value

with open("config.yml", "r") as file:
    config = safe_load(file)

llm_client = AzureChatOpenAI(
    azure_endpoint=config["llm"]["endpoint"],
    azure_deployment=config["llm"]["deployment"],
    api_key=openai_key,
    api_version=config["llm"]["api-version"],
    temperature=config["llm"]["temperature"],
    seed=config["llm"]["seed"]
)
embedding = AzureOpenAIEmbeddings(
    azure_endpoint=config["llm"]["endpoint"],
    openai_api_key=openai_key,
    deployment=config["llm"]["embedding"]
)
mongodb_client = MongoClient(
    host=mongo_conn_string
)
db_client = MongoDBSaver(
    mongodb_client,
    db_name="checkpoints_db",
    collection_name="checkpoints_collection"
)
search_client = SearchClient(
    endpoint=config["azure-ai-search"]["endpoint"],
    index_name=config["azure-ai-search"]["index-name"],
    credential=AzureKeyCredential(ai_search_key)
)
sales_db_cl = mongodb_client["voice_order_assistant"]
sales_coll_cl = sales_db_cl["sales"]

# stock_service = {
#     "username": config["stock_control"]["user"],
#     "password": config["stock_control"]["password"],
#     "client_id": config["stock_control"]["client_id"],
#     "client_secret": config["stock_control"]["client_secret"], 
#     "auth_url": config["stock_control"]["auth_url"],
#     "url"   : config["stock_control"]["url"]
# }

@app.get("/")
async def root():
    return {"message": "Corporate AI Sales Assistant"}


@app.post("/voice_assistant")
async def voice_assistant(
        request_body: RequestModel
):
    text = request_body.VoiceAssistant.VoiceOutput
    session_id = request_body.ConversationID
    cart = request_body.BasketItems
    top_n = request_body.SearchTopN
    cart_list = []
    for i in cart:
        cart_list.append(i.dict())
    cart = cart_list           
    customer_id = request_body.CustomerInfo.CustomerID
    customer_email = request_body.CustomerInfo.CustomerEMail
    suggestion_list = request_body.SuggestionList
    assistant = Agent(
        cart=cart,
        db_client=db_client,
        embedding=embedding,
        llm_client=llm_client,
        search_client=search_client,
        customer_id=customer_id,
        customer_email=customer_email,
        sales_client = sales_coll_cl,
        #stock_service = stock_service,
        top_n=top_n
    )

    result, cart = assistant.run(
        text,
        session_id=session_id
    )
    

    return output_creator(cart, result,session_id,voice_config="")