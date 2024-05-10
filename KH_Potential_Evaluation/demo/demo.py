import streamlit as st
from openai import AzureOpenAI
import numpy as np

# Set up OpenAI API credentials
client = AzureOpenAI(
  azure_endpoint = "https://nlpeastus2.openai.azure.com/", 
  api_key="f6d74aa4e897478395c366db5cb2f72b",  
  api_version="2024-02-15-preview"
)

# Set up Streamlit app
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Create input fields
input1 = st.text_input("Kullanıcı Cevabı")
input2 = st.text_input("Gerçek Cevap")



# Calculate similarity score
if input1 and input2:
    response1 = client.embeddings.create(
    input = input1,
    model= "large-embedding"
    )
    response2 = client.embeddings.create(
        input = input2,
        model = "large-embedding"
    )
    similarity_score = cosine_similarity(response1.data[0].embedding, response2.data[0].embedding)
    st.write(f"Benzerlik Skoru: {similarity_score:.2f}")
