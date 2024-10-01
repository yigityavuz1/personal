import io
import pickle
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain_openai import AzureOpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.callbacks import get_openai_callback
import os
from langchain.chat_models import AzureChatOpenAI
from langchain.chains import RetrievalQA
from langchain.tools import Tool
from langchain.agents import AgentExecutor
from azure.data.tables import TableServiceClient
from langchain.tools import tool
from pydantic import BaseModel, Field
from azure.storage.blob import BlobServiceClient
import fitz_new as fitz
import re
from typing import List
from dotenv import load_dotenv

load_dotenv()

OPENAI_GPT3_API_BASE = os.getenv('OPENAI_GPT3_API_BASE')
OPENAI_AZURE_KEY_GPT3 = os.getenv('OPENAI_AZURE_KEY_GPT3')

# Replace with your Azure Storage account connection string
connection_string = os.getenv('AZURE_STORAGE_CONN_STR')

data_table_service_client = TableServiceClient.from_connection_string(connection_string)
table_name = "TroubleshootingTablesMetadata"
table_client = data_table_service_client.get_table_client(table_name=table_name)
blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_name = "maintenance-vectorstore"
container_client = blob_service_client.get_container_client(container_name)


pdf_file = "data/LM6000_OM_GEK105059_Rev_15.pdf"


def get_links_by_index_and_type(index_values: List[str], type_value: str) -> List[dict]:
    """Retrieve rows from the Links table based on multiple index values and a specific type value."""
    try:
        # Initialize an empty list to store the combined results
        combined_results = []

        # Query the Links table for each index value
        for index_value in index_values:
            query_filter = "index eq '{}' and Type eq '{}'".format(index_value, type_value)

            # Query the table storage using the filter
            with data_table_service_client.get_table_client(table_name="Links") as table_client:
                link_entities = table_client.query_entities(query_filter=query_filter,
                                                            select=["Format", "Type", "URL", "index"])
                
                # Extend the combined results with the results of this query
                combined_results.extend(link_entities)
        return combined_results

    except Exception as e:
        raise Exception(f"An error occurred while querying the table: {str(e)}")

        
        
def get_workpackages(pdf_file):

    reader = fitz.open(pdf_file)
    toc = reader.get_toc()
    level1_toc = [item for item in toc if item[0] == 1]
    level1_toc.append([1, "End", reader.page_count])
    pattern = r'(WP\s\d{4}\s\d{2})'
    wp_dict = {}

    for i, (_, title, page) in enumerate(level1_toc):
        if re.search(pattern, title):
            title = re.search(pattern, title).group(1)
            start = page - 1
            end = level1_toc[i + 1][2] - 2
            wp_text = []
            for wp_page in range(start, end + 1):
                text = reader[wp_page].get_text(sort=True)
                text = text.replace("LM6000 PC\nGEK 105059\nGE Industrial AeroDerivative Gas Turbines\nVolume II\n", "")
                text = text.replace("GE PROPRIETARY INFORMATION - Subject to the restrictions on the cover or first page.\nUNCONTROLLED WHEN PRINTED OR TRANSMITTED ELECTRONICALLY\n", "")
                wp_text.append(text)
            wp_dict[title] = wp_text
    return wp_dict

def string_to_hex(string):
    return string.encode('utf-8').hex()

def hex_to_string(number):
    return bytes.fromhex(number).decode('utf-8')
# Define a function that queries Azure Table storage
@tool
def get_troubleshooting_info() -> list:
    """Fetch rows with 'Symptoms' and 'Troubleshooting_Table_No' columns from the TroubleshootingTablesMetadata table."""
    try:

        # Query to retrieve 'Symptoms' and 'Troubleshooting_Table_No' columns from the table
        entities = table_client.query_entities(
            query_filter="",
            select=['Symptoms', 'Troubleshooting_Table_No']
        )

        # Collect the retrieved entities into a list
        results = [entity for entity in entities]

        return results

    except Exception as e:
        raise Exception(f"An error occurred while querying the table: {str(e)}")


def get_unique_symptoms() -> list:
    """Fetch rows with unique 'Symptoms' column from the TroubleshootingTablesMetadata table."""
    symptom_col = "C" + string_to_hex('Symptoms')
    try:

        # Query to retrieve 'Symptoms' column from the table
        entities = table_client.query_entities(
            query_filter="",
            select=[symptom_col]
        )

        # Collect the retrieved entities into a list
        symptoms = [entity[symptom_col] for entity in entities]
        unique_symptoms = list(set(symptoms))
        return unique_symptoms

    except Exception as e:
        raise Exception(f"An error occurred while querying the table: {str(e)}")


# Usage
# results = get_troubleshooting_info(table_name="YourTableName")
# print(results)

# Define the input schema
class TableRowsQueryInput(BaseModel):
    #table_no: str = Field(..., description="The number of the table to query")
    symptom: str = Field(..., description="The symptom to search for in the table")


# Define the function with the input schema
@tool(args_schema=TableRowsQueryInput)
def get_table_rows(symptom: str) -> str:

    """Retrieve rows from a specified table based on a given table number and symptom."""
    symptom_col = "C" + string_to_hex('Symptoms')

    try:
        # Create a query filter for both table number and symptom
        # query_filter = "Troubleshooting_Table_No eq '{}' and Symptoms eq '{}'".format(table_no, symptom)
        
        
        query_filter = "{} eq '{}'".format(symptom_col, symptom)

        # Query the table storage using the filter
        entities = table_client.query_entities(query_filter)
        # Convert the result to a list for easier handling
        entities = list(entities)
        # Define keys to drop and key name changes
        keys_to_drop = ['PartitionKey', 'RowKey']

        # Transform the list of dicts
        entities = [
            {hex_to_string(k[1:]): v for k, v in d.items() if k not in keys_to_drop}
            for d in entities
        ]

       

        if len(entities) == 0:
            return ""

        # print("Troubleshooting Table: " + str(entities))
        return "Troubleshooting Table: " + str(entities)

    except Exception as e:
        raise Exception(f"An error occurred while querying the table: {str(e)}")

class WPQueryInput(BaseModel):
    # table_no: str = Field(..., description="The number of the table to query")
    question: str = Field(..., description="User question about work packages")




embeddings = AzureOpenAIEmbeddings(
                deployment="embeddings",
                model="text-embedding-ada-002",
                azure_endpoint=OPENAI_GPT3_API_BASE,
                openai_api_type="azure",
                openai_api_key=OPENAI_AZURE_KEY_GPT3,
                chunk_size=1)


llm35 = AzureChatOpenAI(
    deployment_name="entekgpt-35-turbo",
    openai_api_version="2023-07-01-preview",
    openai_api_base=OPENAI_GPT3_API_BASE,
    openai_api_key=OPENAI_AZURE_KEY_GPT3,
    openai_api_type="azure",
    model="gpt-35-turbo",
)

llm = AzureChatOpenAI(
     deployment_name="maintenance-assistant-demo",
     openai_api_version="2024-02-15-preview",
     openai_api_base=OPENAI_GPT3_API_BASE,
     openai_api_key=OPENAI_AZURE_KEY_GPT3,
     openai_api_type="azure",
     model="gpt-4o",
     temperature=0
 )

class OutputSchema(BaseModel):
    answer: str


#@st.cache_resource
def init_wp_agent(pdf_file):
    #text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=100, length_function=len)
    docs = get_workpackages(pdf_file)
    chains = []

    for key, value in docs.items():

        blob_client = container_client.get_blob_client(f"vectorstores/vectorstore_{key}.pkl")
        if blob_client.exists():
            docsearch_data = blob_client.download_blob().readall()
            docsearch = FAISS.deserialize_from_bytes(docsearch_data, embeddings)
            print(f"WP vectorstore vectorstore_{key} is loaded.")
        else:
            #chunks = text_splitter.split_text(text=value)
            chunks = value
            docsearch = FAISS.from_texts(chunks, embedding=embeddings, metadatas=[{"source": key, "page": i} for i in range(len(chunks))] )
            docsearch_data = docsearch.serialize_to_bytes()
            blob_client.upload_blob(docsearch_data, overwrite=True)

        chain = RetrievalQA.from_chain_type(
            llm=llm, chain_type="stuff", retriever=docsearch.as_retriever(), verbose=True, return_source_documents=True
        )

        chains.append(chain)
        

    tools = []
    for title, chain in zip(docs.keys(), chains):
        if "WP" in title:
            desc = "useful for when you need to answer questions about the work package called " + title + ". "
        else:
            continue
        tool =  Tool(
            name=(title + " QA System").replace(" ", "_"),
            func=chain,
            description=desc + "Input should be the same as user input.",
            return_direct=False,
        )
        tools.append(tool)
        


    blob_client = container_client.get_blob_client("vectorstores/vectorstore_wp_summaries.pkl")
    if blob_client.exists():
        docsearch = FAISS.deserialize_from_bytes(blob_client.download_blob().readall(), embeddings)
        print(f"WP vectorstore vectorstore_wp_summaries is loaded.")
    else:
        summaries = []
        for tool, chain in zip(tools, chains):
            summary = chain("Give a concise summary of this workpackage that is well optimized for retrieval.")["result"]
            summary = tool.name + ": " + summary
            summaries.append(summary)
        print(summaries)
        docsearch = FAISS.from_texts(summaries, embedding=embeddings, metadatas=[{"source": key} for key in docs.keys()])
        docsearch_data = docsearch.serialize_to_bytes()
        blob_client.upload_blob(docsearch_data, overwrite=True)

    new_chain = RetrievalQA.from_chain_type(
        llm=llm, chain_type="stuff", retriever=docsearch.as_retriever(), verbose=True, return_source_documents=True
    )


    wp_finder_agent_tool = Tool(
            name="WP ID Finder System".replace(" ", "_"),
            func=new_chain,
            description="useful for when you need to find which work package is relevant to a user question.",
            return_direct=False,
        )
    
    tools.append(wp_finder_agent_tool)
    return tools
    
wp_tools = init_wp_agent(pdf_file)

from langchain_core.utils.function_calling import convert_to_openai_function
wp_tools.append(get_table_rows)
functions = [convert_to_openai_function(f) for f in wp_tools]
llm_binded = llm.bind(functions=functions)


def init():

    template = """You are a helpful maintenance assistant who helps field employees in their job. If the user greets you such as "selam", always greet them with "Merhaba ben KD bakım asistanıyım, \
    GE LM6000 Gaz Türbini ile ilgili sorularınıza yanıt verebilirim" in the language which the user have spoken. Otherwise, DO NOT include this greeting sentence \
    in your outputs. When you give answers, use the language which the user have spoken. In your answers, please also keep in your mind about the chat \
    history between you and the user. Here is the chat history you want to check:
    {chat_history}
 
    You have 3 options for answering technical questions:
 
    1. If the {human_input} mentions an issue with failures/malfunctions or asks you about a symptom for troubleshooting, follow these steps:
        a. Get the exact symptom from these Maintenance Symptoms list: """ + str(get_unique_symptoms()) + """
        b. Using the name, get the relevant table rows by using get_table_rows(symptom) function.
        c. Describe the retrieved table rows by itemizing.

    2. If and only if the user is talking about work packages (WP), you have 2 different options to do. The user may imply work packages \
          with the following formats: WP XXXX XX, WPXXXXXX, wpXXXX XX, wpXXXXXX. For example; WP 4022 00, WP 251000, WP1112 00, wp1512 etc.
        a. If there is no work package number provided and the user wants to find its work package number through a question, find out \
              the work package number using WP_ID_Finder_System(user_question) function.
        b. If and only if the user gives the work package number and asks a question about that relevant work package, \
              use WP_XXXX_XX_QA_System(user_question) function to retrieve the answer.
        DO NOT use above functions if the user does not talk about work packages in his question.

    3. If none of the above, given the following extracted parts of a long document, a question and chat history, provide an answer. \
    Also, using the metadata, be sure to give the sources of the information you get in the form:
    Kaynak: (metadata["source"])
    Sayfa: (metadata["page_number"])
    Here are the relevant documents that you can use to answer user question:
    {context}
   
    Human: {human_input}
    AI:
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template),
            ("user", "{human_input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    memory = ConversationBufferMemory(memory_key="chat_history", input_key="human_input", output_key="output")

    chain1 =   (  {
        "human_input": lambda x: x["human_input"],
        "chat_history": lambda x: x["chat_history"],
        "context": lambda x: x["context"],
                      # Format agent scratchpad from intermediate steps
        "agent_scratchpad": lambda x: format_to_openai_functions(
            x["intermediate_steps"]
        ),
    } | prompt | llm_binded | OpenAIFunctionsAgentOutputParser() )
    qa = AgentExecutor(agent=chain1, tools=wp_tools, verbose=True, memory=memory, max_iterations=2, return_intermediate_steps=True)
    #
    return qa

def read_vectorstore(pkl="vectorstores/main_vectorstore.pkl"):

    blob_client = container_client.get_blob_client(pkl)

    if blob_client.exists():
        print("Loading vectorstore file...")

        # Download the pickle file from Blob Storage
        blob_data = blob_client.download_blob().readall()
        VectorStore = FAISS.deserialize_from_bytes(blob_data, embeddings)

        # Clean up the temporary file
        return VectorStore

    return create_vectorstore(os.path.basename(pdf_file))


import io

def create_vectorstore(pdf):
    blob_client = container_client.get_blob_client(pdf)

    if not blob_client.exists():
        raise FileNotFoundError(f"PDF file '{pdf}' not found in Azure Blob Storage")

    print("Creating vectorstore file...")

    # Download the PDF file from Blob Storage to an in-memory buffer
    pdf_data = blob_client.download_blob().readall()

    store_name = pdf[:-4] + ".pkl"
    reader = fitz.open(stream=io.BytesIO(pdf_data))
    number_of_pages = reader.page_count
    text = ""
    i = 0
    docs = []
    while i < number_of_pages-1:

        first_page_text= reader[i].get_text(sort=True)
        first_page_text = first_page_text.replace("LM6000 PC\nGEK 105059\nGE Industrial AeroDerivative Gas Turbines\nVolume I", "")
        first_page_text = first_page_text.replace("LM6000 PC\nGEK 105059\nGE Industrial AeroDerivative Gas Turbines\nVolume II", "")
        first_page_text = first_page_text.replace("GEK 105059\nLM6000 PC\nVolume I\nGE Industrial AeroDerivative Gas Turbines", "")
        first_page_text = first_page_text.replace("GEK 105059\nLM6000 PC\nVolume II\nGE Industrial AeroDerivative Gas Turbines", "")
        first_page_text = first_page_text.replace("GE PROPRIETARY INFORMATION - Subject to the restrictions on the cover or first page.", "")
        first_page_text = first_page_text.replace("UNCONTROLLED WHEN PRINTED OR TRANSMITTED ELECTRONICALLY", "")
        
        if len(first_page_text) < 10 or (len(first_page_text) < 200 and len(reader[i].get_images(full=True)) > 0):
            i+=1
            continue

        second_page_text= reader[i+1].get_text(sort=True)
        second_page_text = second_page_text.replace("LM6000 PC\nGEK 105059\nGE Industrial AeroDerivative Gas Turbines\nVolume I", "")
        second_page_text = second_page_text.replace("LM6000 PC\nGEK 105059\nGE Industrial AeroDerivative Gas Turbines\nVolume II", "")
        second_page_text = second_page_text.replace("GEK 105059\nLM6000 PC\nVolume I\nGE Industrial AeroDerivative Gas Turbines", "")
        second_page_text = second_page_text.replace("GEK 105059\nLM6000 PC\nVolume II\nGE Industrial AeroDerivative Gas Turbines", "")
        second_page_text = second_page_text.replace("GE PROPRIETARY INFORMATION - Subject to the restrictions on the cover or first page.", "")
        second_page_text = second_page_text.replace("UNCONTROLLED WHEN PRINTED OR TRANSMITTED ELECTRONICALLY", "")
        second_page_text = second_page_text[:300]

        if len(second_page_text) < 10 or (len(second_page_text) < 200 and len(reader[i+1].get_images(full=True)) > 0):
            doc = Document(page_content=first_page_text, metadata={"source":pdf, "page_number":i+1})
            docs.append(doc)
            i += 2
        else:
            total_text = first_page_text + " " + second_page_text
            doc = Document(page_content=total_text, metadata={"source":pdf, "page_number":i+1})
            docs.append(doc)
            i += 1

    #print(docs)
    print("Saving vectorstore")
    VectorStore = FAISS.from_documents(docs, embedding=embeddings)

    # Create a pickle file in an in-memory buffer
    # Upload the pickle data to Azure Blob Storage
    blob_client_upload = container_client.get_blob_client(store_name)
    data = VectorStore.serialize_to_bytes()
    blob_client_upload.upload_blob(data, overwrite=True)

    return VectorStore

# Function to load messages to history from a dictionary
def load_messages_to_history(history, chat_history):
    history.messages = []
    for msg in chat_history:
        if msg.role == "user":
            history.add_user_message(msg.content)
        else:
            history.add_ai_message(msg.content)

#collector = init_feedback()
chain = init()
VectorStore = read_vectorstore()


def get_table_resources(symptom: str) -> list:
    symptom_col = "C" + string_to_hex('Symptoms')

    """Retrieve rows from a specified table based on a given table number and symptom."""
    try:
        # Create a query filter for the symptom
        query_filter = "{} eq '{}'".format(symptom_col, symptom)

        # Query the table storage using the filter
        with data_table_service_client.get_table_client(table_name="TroubleshootingTablesMetadata") as table_client:
            symptom_keys = table_client.query_entities(query_filter=query_filter, select=["C"+ string_to_hex("index"), "C"+ string_to_hex("Table")])

        links = []
        row_table_set = set()
        with data_table_service_client.get_table_client(table_name="TableLinks") as table_client:
            for key in symptom_keys:
                query_filter = "TableRowID eq {} and Table eq '{}'".format(key["C"+ string_to_hex("index")], key["C"+ string_to_hex("Table")])
                link_entities = table_client.query_entities(query_filter=query_filter, select=["LinkID"])
                links.extend(link_entities)
                row_table_set.add(key["C"+ string_to_hex("Table")])


        resources = []
        with data_table_service_client.get_table_client(table_name="Links") as table_client:

            for key in links:
                query_filter = "RowKey eq '{}'".format(key["LinkID"])
                link_entities = table_client.query_entities(query_filter=query_filter,
                                                            select=["Format", "Type", "URL", "index"])
                resources.extend(link_entities)

            for table_name in row_table_set:
                print(table_name)
                query_filter = "URL eq '{}'".format(table_name)
                link_entities = table_client.query_entities(query_filter=query_filter,
                                                            select=["Format", "Type", "URL", "index"])
                resources.extend(link_entities)

        # Return the result list with links
        return resources

    except Exception as e:
        raise Exception(f"An error occurred while querying the table: {str(e)}")

import datetime
async def make_query(prompt):
    # user questions/query
    docs = VectorStore.similarity_search(query=prompt.question, k=3)

    load_messages_to_history(chain.memory.chat_memory, prompt.history)
    with get_openai_callback() as cb:

        #get start time
        start_time = datetime.datetime.now()
        response = chain({
            "human_input": prompt.question,
            "context": docs,
        })
        #get end time
        end_time = datetime.datetime.now()

        #calculate duration
        duration = end_time - start_time
        #durain in seconds
        duration = duration.total_seconds()
        print(f"Duration: {duration} seconds")
        response["resources"] = []
        if len(response["intermediate_steps"]) > 0:
            for intermediate_step in response["intermediate_steps"]:
                message_log = intermediate_step[0]
                
                if message_log.tool == "get_table_rows":
                    print("Getting table resources...")
                    call_output = intermediate_step[1]
                    if call_output != "":
                        message_log = intermediate_step[0]
                        symptom = message_log.tool_input['symptom']
                        response["resources"].extend(get_table_resources(symptom))
                if "QA_System" in message_log.tool or "Finder_System" in message_log.tool:
                    
                    print("Getting cited work package resources...")
                    print(intermediate_step)
                    if intermediate_step[1]:
                        if "source_documents" in intermediate_step[1].keys():
                            source_documents = intermediate_step[1]["source_documents"]
                            doc_names = [doc.metadata["source"] for doc in source_documents]
                            response["resources"].extend(get_links_by_index_and_type(set(doc_names), "Work Package"))
                    else:
                        print("No source documents found.")
        response["resources"] = list(({d['index']: d for d in response["resources"]}).values())

        return response

async def main():
    import datetime
    from pydantic import parse_obj_as
    from schemas import RequestBody

    '''
    qa_pairs = {
    "WP1111 00 hakkında bana bilgi verir misin?":"",
    "XN25 sensör hangi parçanın hızını ölçer?": "Bu sensör HPC(high pressure turbine) hızını ölçer.",
    "HPC(high pressure turbine) hızı hangi sesnsör ile ölçülür?": "XN25 sensörü ile ölçüm yapılır.",
    "Hıgh pressure turbine sensor değişimi için ilgili workpackage numarasını söyler misin?": "WP 1816 00",
    "XN25 sensor değişimi için ilgili workpackage numarasını söyler misin?": "WP 1816 00",
    "WP 1816 00 numarası hangi işlem için oluşturulmuş bir dökümandır?": "Hıgh pressure turbine sensor değişimi için ilgili workpackage'dır.",
    "variable geometry system ile alakalı tabloyu görebilir miyim?": "Sayfa 223 ve 224 'te oluşmuş tablo bilgisini göstermesi gerekir.",
    "Variable geometry system ile ilgili muhtemel olay ve hataları yazabilir misin?": "Sayfa 223 ve 224 'te oluşmuş tabloyu okuyarak yorumlasını bekleriz.",
    "Flameout sinyali hangi durumda göz ardı edilir?": "XN25'in 9.500 rpm'den büyük olması durumunda alev sönmesi sinyali kontrol tarafından göz ardı edilir",
    "dişli kutusunun sol tarafında kaç adet XN25 sensörü bulunur?": "2 adet",
    "XN 25 sensörü değişimi sırasında dikkat etmem gerekn uyarılar nelerdir?": "WP 181600 içindeki warning ve caution kısımlarını özetleyebilir.",
    "XN25 sensörü değişimi sırasında ihtiyacım olan ana ve yardımcı ekipman veya aletler nelerdir? bu ekipmanların part no nedir?": "Wrench, Strap (1/2” drive, 90° angle, 1/2” strap) (Optional) BT-BS-625, Daniels Mfg Corp. Pliers, Teflon-Jawed Local Purchase",
    "Türbin güç üretimi olması gerekenden daha düşük. Sebebi ne olabilir?": "Dirty or damaged low or high pressure compressors VIGVs too closed 1. Improper rig 4. PS3 sensor reading too low 6. T2 reading too low",
    "T2 sensörü çok düşük değer okuyorsa soruyn nasıl giderilebilir ya da düzeltici aksiyon nedir?": "Diğer giriş sıcaklıklarıyla karşılaştırın; Tablo 10-7'ye göre direnci kontrol edin (burada tabloyu getirmesini planlamıştık.) WP 1111 00'a göre sensör değişimi yapabilirsiniz."
    "Türbinde start vermeden önce kontrol etmem gereken ekipman ya da süreçler mevcut mu? hangi ekipmanları, vanaları ya da benzeri elemanları kontrol etmem gerekir?"

    }
    '''
    qa_pairs = {
    #    "High pressure turbine sensor değişimi için ilgili workpackage numarasını söyler misin?": "WP 1816 00",
#        "XN25 sensor değişimi için ilgili workpackage numarasını söyler misin?" : "WP 1816 00",
#"Türbinde start vermeden önce kontrol etmem gereken ekipman ya da süreçler mevcut mu? hangi ekipmanları, vanaları ya da benzeri elemanları kontrol etmem gerekir?":"",
"1q1q: torkmotor arızası alıyorum. ne yapabilirim?":"",
#"Türbin güç üretimi olması gerekenden daha düşük. Sebebi ne olabilir?":"",
#"1q1q: Türbin güç üretimi olması gerekenden daha düşük. Sebebi ne olabilir?":"",
#"Flameout sinyali hangi durumda göz ardı edilir?": "XN25'in 9.500 rpm'den büyük olması durumunda alev sönmesi sinyali kontrol tarafından göz ardı edilir",
# "Türbin güç üretimi olması gerekenden daha düşük. Bu hata için ne yapabilirim?":"",
# "1q1q: Türbin güç üretimi olması gerekenden daha düşük. Bu hata için ne yapabilirim?":""    


    }

    #make dataframe {duration}, {question}, {response["output"]}, {expected_answer}, {response}
    import pandas as pd
    import datetime

    results_df = pd.DataFrame(columns=["duration", "question", "response", "expected_answer", "whole_response"])


    # for each question
    for question, expected_answer in qa_pairs.items():
        prompt = {
            "question": question,
            "history": [
                {
                    "role": "",
                    "content": ""
                }
            ]
        }
        request_body = parse_obj_as(RequestBody, prompt)

        #start seconds
        start = datetime.datetime.now()
        response = await make_query(request_body)
        #response = {"output": "\nasdfasf,afdsaf\n"}
        #end seconds
        end = datetime.datetime.now()
        #calculate duration
        duration = end - start
        #durain in seconds
        duration = duration.total_seconds()
        
        # save it to a csv
        

        # add to df
        new_row = {"duration": duration, "question": question, "response": response["output"], "expected_answer": expected_answer, "resources":response["resources"], "whole_response": response}
        # get date of today
        for i in response["context"]:
            print(i)
        #print(new_row)
        results_df = pd.concat([results_df, pd.DataFrame([new_row])], ignore_index=True)
        today_date = datetime.date.today().strftime("%d-%m-%Y")
    
    # save to csv
    results_df.to_csv(f"results_{today_date}_wp_link.csv")


#if __name__ == "__main__": 
#    import asyncio
   
#    asyncio.run(main())
#    main()
