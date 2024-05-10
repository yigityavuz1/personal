import streamlit as st  
from prompt import PROMPT
from openai import AzureOpenAI
  
# Replace with your own OpenAI API key  
client = AzureOpenAI(
  azure_endpoint = "https://openai-okrsuggestion-hrsub5.openai.azure.com/", 
  api_key="8fbe6a8ea63f4dbdb494e92b559e322b",  
  api_version="2024-02-15-preview"
)
  
# Initialize the OpenAI client with your API key  
  
# Define a function to make the API call using the OpenAI SDK  
def get_openai_score(question,ideal_answer,user_answer):
    prompt = PROMPT.format(question=question, ideal_answer=ideal_answer, user_answer=user_answer)  
    message_text = [{"role":"system","content":prompt},{"role":"user","content":"Score the user's answer out of 10 and give explanation."}]
    try:
        completion = client.chat.completions.create(
            model="gpt4turbo-okrsuggestion-hrsub5", # model = "deployment_name"
            messages = message_text,
            temperature=0.7,
            max_tokens=800,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None
            )
        return completion
    except client.error.OpenAIError as e:  
        return {"error": str(e)}  
  
# Create a Streamlit app  
def main():  
    st.title("OpenAI Scoring App")  
  
    # Input fields  
    input1 = st.text_input("Question")  
    input2 = st.text_input("Ideal Answer")
    input3 = st.text_input("User's Answer")  
  
    # Submit button  
    if st.button("Calculate Score"):  
        # Make the API call using the OpenAI SDK  
        result = get_openai_score(question=input1,ideal_answer=input2,user_answer=input3)  
  
        # Display the result  
        st.write(result.choices[0].message.content)
  
if __name__ == "__main__":  
    main()  
