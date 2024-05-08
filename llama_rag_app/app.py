from api_keys import OPENAI_AZURE_KEY, OPENAI_API_BASE, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
from langchain.vectorstores import FAISS
from langchain.callbacks import get_openai_callback
import streamlit as st
from langchain_community.llms import Bedrock
from langchain_openai import AzureOpenAIEmbeddings
import os

os.environ['AWS_ACCESS_KEY_ID'] = AWS_ACCESS_KEY_ID
os.environ['AWS_SECRET_ACCESS_KEY'] = AWS_SECRET_ACCESS_KEY
os.environ['AWS_DEFAULT_REGION'] = AWS_DEFAULT_REGION

os.environ['AZURE_OPENAI_ENDPOINT'] = OPENAI_API_BASE
os.environ['AZURE_OPENAI_API_KEY'] = OPENAI_AZURE_KEY

embeddings = AzureOpenAIEmbeddings(
                deployment="embeddings",
                model="text-embedding-ada-002",
                openai_api_type="azure",
                chunk_size=1)

llm = Bedrock(
     model_id="meta.llama3-8b-instruct-v1:0"
)

if 'first_button' not in st.session_state:
    st.session_state.first_button = False

def extract_campaign_name_and_content(text):
    campaign_name = "Unknown Campaign"
    remaining_content = text
    lines = text.split(", ")
    for line in lines:
        if line.startswith("{Kampanya :"):
            campaign_name = line.split(":", 1)[1].strip()
            remaining_content = text.replace(line + ", ", "")  # Remove the 'Kampanya' line from the content
            break
    return campaign_name, remaining_content

def first_submit_button():
    st.session_state.first_button = True

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

def rag(query, vectorstore):
    docs = vectorstore.similarity_search(query=query, k=3)
    prompt_format = """ Sen Türkçe konuşan bir asistansın. Görevin, sana verilen dökümanları kullanarak, kullanıcının verdiği talimatlara doğru, etik ve Türkçe yanıt vermek.
### Döküman
{}
### Talimat
{}
### Yanıt
"""
    response = llm.generate([prompt_format.format(docs,query)], temperature=0.2, top_p=0.3, stop=["### Talimat","###"])
    return response.generations[0][0].text

if check_password():
    st.title("OPET Chatbot")
    
    
    VectorStore = FAISS.load_local('opet_faiss_0213',embeddings=embeddings, allow_dangerous_deserialization=True)
    
    
    query_text = st.text_input("Enter your question:", key=0)
    st.session_state.query_text = query_text
    button = st.button('Submit',on_click=first_submit_button)
    #clear_button = st.button('Clear Chat Memory')
    #memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

    # number_k = st.number_input("Insert a number for k:", value=3, placeholder="Type a number...")

    if button:
            
        docs = VectorStore.similarity_search(query=query_text, k=3)
        
        with get_openai_callback() as cb:
            response = rag(query_text, VectorStore)
            st.session_state.response = response
            st.session_state.cb = cb
        
        st.header('Yapay Zeka cevabı')
        st.write(response)
        st.header('Kampanya Metni')
        #st.write(docs[0].page_content)

        campaigns = [extract_campaign_name_and_content(doc.page_content) for doc in docs]
        tab_titles = [campaign_name for campaign_name, _ in campaigns]

        tabs = st.tabs(tab_titles)
        for idx, tab in enumerate(tabs):
            with tab:
                content = campaigns[idx][1]
                st.write(content)
        

    st.write('---')
    st.subheader('Feedback')    
    feedback = st.text_input('What do you think about answer?',key='feedback')
    
    feedback_button = st.button('Submit',key='feedback_button')
    

    if st.session_state['feedback_button']==True:
        
        with open('feedback.txt','a',encoding='utf-8') as f:
            f.writelines('Feedback:{feedback_text}'.format(feedback_text=st.session_state.feedback))
            f.writelines('\n')
            f.writelines(str(st.session_state.cb))
            f.writelines('\n')
            f.writelines('Query_Text:{query}'.format(query=st.session_state.query_text))
            f.writelines('\n')
            f.writelines('Response:{response_text}'.format(response_text=st.session_state.response))
            f.writelines('\n')
            f.writelines('##')
            f.writelines('\n\n')
            
            f.close()
