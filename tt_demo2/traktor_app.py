from api_keys import OPENAI_AZURE_KEY_GPT3, OPENAI_AZURE_KEY_GPT4, OPENAI_GPT3_API_BASE, OPENAI_GPT4_API_BASE, OPENAI_API_KEY
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains.question_answering import load_qa_chain
from langchain.callbacks import get_openai_callback
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
import streamlit as st
from PIL import Image
from langchain.document_loaders import PyPDFLoader
from langchain.memory import ConversationBufferMemory
from langchain.chains import RetrievalQA
from langchain.chains import ConversationalRetrievalChain

embeddings = OpenAIEmbeddings(
                deployment="embeddings",
                model="text-embedding-ada-002",
                openai_api_base=OPENAI_GPT3_API_BASE,
                openai_api_type="azure",
                openai_api_key=OPENAI_AZURE_KEY_GPT3,
                chunk_size=1)


llm = AzureChatOpenAI(
    deployment_name="35-turbo-deployment",
    openai_api_version="2023-03-15-preview",
    openai_api_base=OPENAI_GPT3_API_BASE,
    openai_api_key=OPENAI_AZURE_KEY_GPT3,
    openai_api_type="azure",
    model="gpt-35-turbo",
)



def check_password():
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if (
            st.session_state["username"] in st.secrets["passwords"]
            and st.session_state["password"]
            == st.secrets["passwords"][st.session_state["username"]]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store username + password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show inputs for username + password.
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input("Username", on_change=password_entered, key="username")
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 User not known or password incorrect")
        return False
    else:
        # Password correct.
        return True

if check_password():
    st.title("TurkTraktor Service Assistant")
    VectorStore = FAISS.load_local('turktraktor_faiss',embeddings=embeddings)
    query_text = st.text_input("Enter your question:", key=0)
    button = st.button('Submit')
    #clear_button = st.button('Clear Chat Memory')
    #memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)


    if button:

        
        
        
        
        docs = VectorStore.similarity_search(query=query_text, k=3)
        print(docs)
        
        chain = load_qa_chain(llm=llm, chain_type="stuff")  #

        with get_openai_callback() as cb:
            response = chain.run(input_documents=docs, question=query_text)
            print(cb)

        st.write(response)



