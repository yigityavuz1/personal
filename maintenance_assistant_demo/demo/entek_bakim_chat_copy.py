import streamlit as st
import pickle
from PyPDF2 import PdfReader
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.memory import ConversationBufferWindowMemory, ConversationBufferMemory
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import RetrievalQA
from langchain.retrievers.multi_vector import SearchType
from langchain.callbacks import get_openai_callback
from langchain.docstore.document import Document
import os
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.agents import initialize_agent, AgentExecutor

from trubrics.integrations.streamlit import FeedbackCollector
import uuid
from azure.data.tables import TableServiceClient
from langchain.tools import tool
from pydantic.v1 import BaseModel, Field
from langchain.tools.render import format_tool_to_openai_function
from langchain_core.messages.human import HumanMessage
from langchain_core.messages.ai import AIMessage
import sys
import time
# Import things that are needed generically
from langchain.agents import AgentType, initialize_agent
from langchain_openai import AzureOpenAIEmbeddings
from langchain.tools import Tool


# setting path
#sys.path.append('/storage/data/CV/okr-analytics/okr-analytics/ekin/brain-demos/brain_demos')

from api_keys import OPENAI_AZURE_KEY_GPT3, OPENAI_AZURE_KEY_GPT4, OPENAI_GPT3_API_BASE, OPENAI_GPT4_API_BASE, OPENAI_API_KEY

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "Sana nasıl yardımcı olabilirim?"}]
if "prompt_ids" not in st.session_state:
    st.session_state["prompt_ids"] = []
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

import fitz_new as fitz
import re

pdf_file = "LM6000_OM_GEK105059_Rev_15.pdf"


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
            wp_text = ""
            for wp_page in range(start, end + 1):
                wp_text += reader[wp_page].get_text()
            wp_dict[title] = wp_text

    reader.close()
    return wp_dict

def string_to_hex(string):
    return string.encode('utf-8').hex()

def hex_to_string(number):
    return bytes.fromhex(number).decode('utf-8')

# Replace with your Azure Storage account connection string
connection_string = "DefaultEndpointsProtocol=https;AccountName=entekopenaimaintenance;AccountKey=U+bCtvDS3XVjbEpcvg4A1upVGUlVKXP9ClXXZ67aDQ9B5qcYZXdvWoZaGqrCFJ/8l7UlKCJnMzg/+ASt7C8hFg==;EndpointSuffix=core.windows.net"

data_table_service_client = TableServiceClient.from_connection_string(connection_string)
table_name = "TroubleshootingTablesMetadata"
table_client = data_table_service_client.get_table_client(table_name=table_name)



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
        with data_table_service_client.get_table_client(table_name="TableLinks") as table_client:
            for key in symptom_keys:
                query_filter = "TableRowID eq {} and Table eq '{}'".format(key["C"+ string_to_hex("index")], key["C"+ string_to_hex("Table")])
                link_entities = table_client.query_entities(query_filter=query_filter, select=["LinkID"])
                links.extend(link_entities)
        resources = []
        with data_table_service_client.get_table_client(table_name="Links") as table_client:

            for key in links:
                query_filter = "RowKey eq '{}'".format(key["LinkID"])
                link_entities = table_client.query_entities(query_filter=query_filter,
                                                            select=["Format", "Type", "URL", "index"])
                resources.extend(link_entities)

        # Return the result list with links
        return resources

    except Exception as e:
        raise Exception(f"An error occurred while querying the table: {str(e)}")

# Function to return memory as a dictionary
def get_chat_history_as_dict(history):
    return {
        "messages": [
            {"content": message.content, "sender": "user" if isinstance(message, HumanMessage) else "AI"}
            for message in history.messages
        ]
    }

# Function to load messages to history from a dictionary
def load_messages_to_history(history, chat_history):
    history.messages = []
    for msg in chat_history["messages"]:
        if msg["sender"] == "user":
            history.add_user_message(msg["content"])
        else:
            history.add_ai_message(msg["content"])

# Define a function that queries Azure Table storage
@tool
def get_troubleshooting_info() -> list:
    """Fetch rows with 'Symptoms' and 'Troubleshooting_Table_No' columns from the TroubleshootingTablesMetadata table."""
    try:
        start_time = time.time()
        print(f"Start querying troubleshooting info at {start_time}")
        # Query to retrieve 'Symptoms' and 'Troubleshooting_Table_No' columns from the table
        entities = table_client.query_entities(
            query_filter="",
            select=['Symptoms', 'Troubleshooting_Table_No']
        )

        # Collect the retrieved entities into a list
        results = [entity for entity in entities]
        end_time = time.time()

        execution_time = end_time - start_time
        print(f"Troubleshooting query execution time: {execution_time} seconds")

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
    symptom: str = Field(..., description="The symptom to search for in the table if the user makes a query about failures/malfunctions")

# Define the function with the input schema
@tool(args_schema=TableRowsQueryInput)
def get_table_rows(symptom: str) -> str:

    """Retrieve rows from a specified table based on a given table number and symptom."""
    symptom_col = "C" + string_to_hex('Symptoms')

    try:
        # Create a query filter for both table number and symptom
        # query_filter = "Troubleshooting_Table_No eq '{}' and Symptoms eq '{}'".format(table_no, symptom)
        start_time = time.time()
        print(f"Start querying troubleshooting info at {start_time}")
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

        end_time = time.time()

        execution_time = end_time - start_time
        print(f"Troubleshooting query execution time: {execution_time} seconds")

        if len(entities) == 0:
            return ""

        # print("Troubleshooting Table: " + str(entities))
        return "Troubleshooting Table: " + str(entities)

    except Exception as e:
        raise Exception(f"An error occurred while querying the table: {str(e)}")


class WPQueryInput(BaseModel):
    # table_no: str = Field(..., description="The number of the table to query")
    question: str = Field(..., description="User question about work packages")


@tool(args_schema=WPQueryInput)
def get_wp_info(question: str) -> str:
    """Get answer about the work package if a work package is mentioned."""
    return wp_agent.run(question)


tools = [get_table_rows, get_wp_info]
functions = [format_tool_to_openai_function(f) for f in tools]


embeddings = AzureOpenAIEmbeddings(
                deployment="embeddings",
                model="text-embedding-ada-002",
                azure_endpoint=OPENAI_GPT3_API_BASE,
                openai_api_type="azure",
                openai_api_key=OPENAI_AZURE_KEY_GPT3,
                chunk_size=1)
"""llm2 = AzureChatOpenAI(
    deployment_name="entekgpt-35-turbo-16k",
    openai_api_version="2023-07-01-preview",
    openai_api_base=OPENAI_GPT3_API_BASE,
    openai_api_key=OPENAI_AZURE_KEY_GPT3,
    openai_api_type="azure",
    model="gpt-35-turbo-16k",
    temperature=0
)"""

"""llm = AzureChatOpenAI(
    deployment_name="entekgpt-35-turbo",
    openai_api_version="2023-07-01-preview",
    openai_api_base=OPENAI_GPT3_API_BASE,
    openai_api_key=OPENAI_AZURE_KEY_GPT3,
    openai_api_type="azure",
    model="gpt-35-turbo",
    temperature=0
)"""



llm = AzureChatOpenAI(
    deployment_name="entekgpt-4",
    openai_api_version="2023-07-01-preview",
    openai_api_base=OPENAI_GPT3_API_BASE,
    openai_api_key=OPENAI_AZURE_KEY_GPT3,
    openai_api_type="azure",
    model="gpt-4",
    temperature = 0
)


llm_binded = llm.bind(functions=functions)

class OutputSchema(BaseModel):
    answer: str

@st.cache_resource
def init_wp_agent(pdf_file):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=100, length_function=len)
    docs = get_workpackages(pdf_file)
    chains = []

    docs = get_workpackages(pdf_file)
    for key, value in docs.items():

        if os.path.exists(f"vectorstore_{key}"):
            docsearch = FAISS.load_local(f"vectorstore_{key}", embeddings, allow_dangerous_deserialization=True)
            print(docsearch, "BURAAASII")
            print(f"WP vectorstore vectorstore_{key} is loaded.")
        else:
            chunks = text_splitter.split_text(text=value)
            docsearch = FAISS.from_texts(chunks, embedding=embeddings)
            docsearch.save_local(f"vectorstore_{key}")


        chain = RetrievalQA.from_chain_type(
            llm=llm, chain_type="stuff", retriever=docsearch.as_retriever(), verbose=True
        )

        chains.append(chain)

    tools = []
    for title, chain in zip(docs.keys(), chains):
        if "WP" in title:
            desc = "useful for when you need to answer questions about the work package called " + title + ". "
        else:
            continue
        tool =  Tool(
            name=title + " QA System",
            func=chain.run,
            description=desc + "Input should be the same as user input.",
            return_direct=True,
        )
        tools.append(tool)
    wp_agent = initialize_agent(
        tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True, handle_parsing_errors=True
    )

    return wp_agent
@st.cache_resource
def init():

    template = """You are a maintenance assistant having conversation with a human.

    Maintenance Symptoms: """ + str(get_unique_symptoms()) + """

    1. Check if the user is talking about a similar issue that could be above symptoms, and follow these steps:
    - Get the exact symptom name matches. 
    - Using the name, get the relevant table rows by using get_table_rows(symptom) function.
    - Describe the retrieved table rows by itemizing.
    2. If user is asking about a work package (WP), retrieve the answer using get_wp_info(user_question) function.
    3. If you cannot find any info, given the following extracted parts of a long document and a question and chat history, provide an answer.
    4. When you give answers, use the language which the user have spoken.
    {context}

    {chat_history}
    Human: {human_input}
    AI:
    """

    template = """You are a maintenance assistant for having conversation with a human. You belong to the company named Entek which is
    Turkish company for electricity distribution. If the user starts conversation with a greeting, greet them with "Merhaba, ben Entek
    asistanıyım. Size nasıl yardımcı olabilirim?" in the language which the user have spoken.

    You have 5 main tasks for this purpose:

    1. If and only if the user is having an issue with failures/malfunctions or asks you about a symptom for troubleshooting, follow these steps:
        a. Get the exact symptom from these Maintenance Symptoms list: """ + str(get_unique_symptoms()) + """
        b. Using the name, get the relevant table rows by using get_table_rows(symptom) function.
        c. Describe the retrieved table rows by itemizing.
    2. If and only if the user is asking about a work package (WP) with an id, retrieve the answer using get_wp_info(user_question) function.
    If there is no work package ids, do not use get_wp_info(user_question) function.
        -Example work package names(ids) are like this: WP 4022 00, WP 2510 00 etc.
    3. If none of the above, given the following extracted parts of a long document and a question and chat history, provide an answer. 
    Here are the relevant documents that you can use to answer user question: 
    {context}    
    4. When you give answers, use the language which the user have spoken.
    5. In your answers, please also keep in your mind about the chat history between you and the user.
    Here is the chat history you want to check: 
    {chat_history}
    
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
    #chain = prompt | llm | OpenAIFunctionsAgentOutputParser()

    chain1 =   (  {
        "human_input": lambda x: x["human_input"],
        "chat_history": lambda x: x["chat_history"],
        "context": lambda x: x["context"],
                      # Format agent scratchpad from intermediate steps
        "agent_scratchpad": lambda x: format_to_openai_functions(
            x["intermediate_steps"]
        ),
    } | prompt | llm_binded | OpenAIFunctionsAgentOutputParser())

    qa = AgentExecutor(agent=chain1, tools=tools, verbose=True, memory=memory, max_iterations=2, return_intermediate_steps=True)
    #qa = AgentExecutor(agent=chain1, tools=tools, verbose=True, memory=memory, max_iterations=2, include_run_info=True)

    return qa




@st.cache_data
def init_feedback():

    # 1. authenticate with trubrics
    collector = FeedbackCollector(
        email="oyku.bayramoglu@kocdigital.com",
        password="P049619!",
        project="entek_bakim"
    )
    return collector

collector = init_feedback()
chain = init()
wp_agent = init_wp_agent(pdf_file)
messages = st.session_state.messages


# Page 1
def page1():


    st.title("Bakım Asistanı")

    # File upload
    pdf = "LM6000_OM_GEK105059_Rev_15.pdf"

    if pdf is not None:

        # embeddings
        store_name = pdf[:-4]
        if os.path.exists(f"vectorstore_{store_name}_1"):
            VectorStore = FAISS.load_local(f"vectorstore_{store_name}_1", embeddings, allow_dangerous_deserialization=True)

        else:
            pdf_reader = PdfReader(pdf)
            pages = pdf_reader.pages
            text = ""
            chunked_docs = []
            for page in pages[:3]:
                text = page.extract_text()

            #text_splitter = RecursiveCharacterTextSplitter(
            #    chunk_size=1000,
            #    chunk_overlap=200,
            #    length_function=len
            #)

            chunks = text_splitter.split_text(text=text)
            VectorStore = FAISS.from_texts(chunks, embedding=embeddings)
            VectorStore.save_local(f"vectorstore_{store_name}_1")



        for n, msg in enumerate(messages):
            st.chat_message(msg["role"]).write(msg["content"])

            if msg["role"] == "assistant" and n > 1:
                feedback_key = f"feedback_{int(n / 2)}"

                if feedback_key not in st.session_state:
                    st.session_state[feedback_key] = None
                feedback = collector.st_feedback(
                    component="default",
                    feedback_type="thumbs",
                    open_feedback_label="[Opsiyonel] Ek geribildirim verin",
                    model="entek-gpt-3.5",
                    key=feedback_key,
                    prompt_id=st.session_state.prompt_ids[int(n / 2) - 1],
                )
                if feedback:
                    with st.sidebar:
                        st.write(feedback)
        # user questions/query
        if prompt := st.chat_input("Sorularınızı buradan sorabilirsiniz"):
            messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            print("MAKING QUERY...")
            start_time = time.time()
            print(f"Starting similar vectors query at {start_time}")
            docs = VectorStore.similarity_search(query=prompt, k=3)
            print(docs)
            end_time = time.time()
            execution_time = end_time - start_time

            print(f"Vectorstore query execution time: {execution_time} seconds")
            #docs = ""

            with get_openai_callback() as cb:
                #load_messages_to_history(chain.memory.chat_memory, chat_history_example)
                #print("MEMORY")
                #print(chain.memory.chat_memory)
                start_time = time.time()
                print(f"Starting openai query at {start_time}")
                response = chain({
                    "human_input": prompt,
                    "context": docs,
                })
                end_time = time.time()
                execution_time = end_time - start_time

                print(f"Openai response execution time: {execution_time} seconds")

                print(cb)
                if len(response["intermediate_steps"]) > 0:
                    call_output = response["intermediate_steps"][0][1]
                    #if call_output != "":
                    #    message_log = response["intermediate_steps"][0][0]
                    #    symptom = message_log.tool_input['symptom']
                    #    response["resources"] = get_table_resources(symptom)


            st.write(response["output"])

            st.session_state.logged_prompt = collector.log_prompt(
                config_model={"model": "gpt-3.5-turbo"},
                prompt=prompt,
                generation=response["output"],
                session_id=st.session_state.session_id,
            )

            st.session_state.prompt_ids.append(st.session_state.logged_prompt.id)
            messages.append({"role": "assistant", "content": response})
            #st.rerun()  # force rerun of app, to load last feedback component


# Sidebar navigation
sidebar_options = {
    "Entek - Bakım Asistanı": page1,
    #"Entek - Troubleshooting Demo GPT3": page3
}


# Main application
def main():

    

    st.sidebar.title("🦜🔗 KoçDigital OpenAI & LLM Demos")
    page = st.sidebar.radio("", list(sidebar_options.keys()))

    # Execute the selected page function
    sidebar_options[page]()

if __name__ == "__main__":
    main()
