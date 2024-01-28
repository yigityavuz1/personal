import requests
import time

from openai import AzureOpenAI
import gradio as gr

CLIENT = AzureOpenAI(
    azure_endpoint="https://nlpeastus2.openai.azure.com/",
    api_key="f6d74aa4e897478395c366db5cb2f72b",
    api_version="2023-07-01-preview"
)


def improve_okr(old_text):
    params_obj = {
        "SessionID": "96B889AE-CFDC-497B-920A-970FF861C6D4",
        "UserID": "48D689C9-7A92-436D-3D48-08D9DAD35B22",
        "ObjectiveID": "0001",
        "Objective": old_text
    }
    start_time = time.time()
    response = requests.post('http://localhost:3000/improve_objective/', json=params_obj).json()
    end_time = time.time()
    response_time = end_time - start_time
    return response['NewObjectives'], response_time


def improve_kr(old_text):
    params_kr = {
        "SessionID": "96B889AE-CFDC-497B-920A-970FF861C6D4",
        "UserID": "48D689C9-7A92-436D-3D48-08D9DAD35B22",
        "KeyResultID": "0001",
        "KeyResult": old_text
    }
    start_time = time.time()
    response = requests.post('http://localhost:3000/improve_key_result/', json=params_kr).json()
    end_time = time.time()
    response_time = end_time - start_time
    return response['NewKeyResult'], response_time


def okr_chatbot(user_msg, user_name, company_name, company_group, department, position, hire_date, chat_history, type):
    params_chat = {
        "SessionID": "96B889AE-CFDC-497B-920A-970FF861C6D4",
        "UserID": "48D689C9-7A92-436D-3D48-08D9DAD35B22",
        "UserName": user_name,
        "CompanyName": company_name,
        "CompanyGroup": company_group,
        "Department": department,
        "Position": position,
        "HireDate": hire_date,
        "UserMessage": user_msg,
        "ChatHistory": chat_history
    }
    start_time = time.time()

    if type == 1:
        response = requests.post('http://localhost:3000/okr_suggestion_chat/', json=params_chat).json()
    elif type == 2:
        response = requests.post('http://localhost:3000/development_kr_suggestion_chat/', json=params_chat).json()
    elif type == 3:
        response = requests.post('http://localhost:3000/aligned_okr_suggestion_chat/', json=params_chat).json()
    else:
        response = requests.post('http://localhost:3000/okr_chat/', json=params_chat).json()

    end_time = time.time()
    response_time = end_time - start_time
    return response['LLMAnswer'], response_time


with gr.Blocks() as demo:
    gr.Markdown("""
    # KoçDigital - KH OKR Suggestion Demo 🚀‍👩‍🚀👨‍🏫🤖
    """)

    with gr.Tab("Improve Objectives"):
        okr_input = gr.Textbox(label="Old Objective Text")
        okr_button = gr.Button("Submit")
        okr_output = gr.Textbox(label="New Objective Texts")
        response_time_output1 = gr.Textbox(label="Response Time")

    with gr.Tab("Improve Key Results"):
        kr_input = gr.Textbox(label="Old Key Result Text")
        kr_button = gr.Button("Submit")
        kr_output = gr.Textbox(label="New Key Result Text")
        response_time_output2 = gr.Textbox(label="Response Time", elem_id='2')

    with gr.Tab("OKR/KR Suggestion Virtual Assistant"):
        chatbot = gr.Chatbot()
        msg = gr.Textbox(label="Your Message")
        response_time_output3 = gr.Textbox(label="Response Time", elem_id='3')
        user_name = gr.Textbox(label="User Name")
        company_name = gr.Textbox(label="Company Name")
        company_group = gr.Textbox(label="Company Group")
        department = gr.Textbox(label="Department")
        position = gr.Textbox(label="Position")
        hire_date = gr.Textbox(label="Hire Date")

        clear = gr.ClearButton([msg, chatbot])


        def respond(message, chat_history, user_name, company_name, company_group, department, position, hire_date):
            history = []
            if len(chat_history) < 4:
                for i in range(len(chat_history)):
                    history.append(
                        {'role': 'user',
                         'content': chat_history[i][0]}
                    )
                    history.append(
                        {'role': 'assistant',
                         'content': chat_history[i][1]}
                    )

            bot_message, response_time_output = okr_chatbot(message, user_name, company_name, company_group, department,
                                                            position, hire_date, history, 1)
            chat_history.append((message, bot_message))
            time.sleep(2)
            return "", chat_history, response_time_output


        msg.submit(respond, [msg, chatbot, user_name, company_name, company_group, department, position, hire_date],
                   [msg, chatbot, response_time_output3])

    with gr.Tab("Development KR Suggestion Virtual Assistant"):
        chatbot = gr.Chatbot()
        msg = gr.Textbox(label="Your Message")
        response_time_output4 = gr.Textbox(label="Response Time", elem_id='4')
        user_name = gr.Textbox(label="User Name")
        company_name = gr.Textbox(label="Company Name")
        company_group = gr.Textbox(label="Company Group")
        department = gr.Textbox(label="Department")
        position = gr.Textbox(label="Position")
        hire_date = gr.Textbox(label="Hire Date")

        clear = gr.ClearButton([msg, chatbot])


        def respond(message, chat_history, user_name, company_name, company_group, department, position, hire_date):
            history = []
            if len(chat_history) < 4:
                for i in range(len(chat_history)):
                    history.append(
                        {'role': 'user',
                         'content': chat_history[i][0]}
                    )
                    history.append(
                        {'role': 'assistant',
                         'content': chat_history[i][1]}
                    )

            bot_message, response_time_output = okr_chatbot(message, user_name, company_name, company_group, department,
                                                            position, hire_date, history, 2)
            chat_history.append((message, bot_message))
            time.sleep(2)
            return "", chat_history, response_time_output


        msg.submit(respond, [msg, chatbot, user_name, company_name, company_group, department, position, hire_date],
                   [msg, chatbot, response_time_output4])

    with gr.Tab("Aligned OKR/KR Suggestion Virtual Assistant"):
        chatbot = gr.Chatbot()
        msg = gr.Textbox(label="Your Message")
        response_time_output5 = gr.Textbox(label="Response Time", elem_id='5')
        user_name = gr.Textbox(label="User Name")
        company_name = gr.Textbox(label="Company Name")
        company_group = gr.Textbox(label="Company Group")
        department = gr.Textbox(label="Department")
        position = gr.Textbox(label="Position")
        hire_date = gr.Textbox(label="Hire Date")

        clear = gr.ClearButton([msg, chatbot])


        def respond(message, chat_history, user_name, company_name, company_group, department, position, hire_date):
            history = []
            if len(chat_history) < 4:
                for i in range(len(chat_history)):
                    history.append(
                        {'role': 'user',
                         'content': chat_history[i][0]}
                    )
                    history.append(
                        {'role': 'assistant',
                         'content': chat_history[i][1]}
                    )

            bot_message, response_time_output = okr_chatbot(message, user_name, company_name, company_group, department,
                                                            position, hire_date, history, 3)
            chat_history.append((message, bot_message))
            time.sleep(2)
            return "", chat_history, response_time_output


        msg.submit(respond, [msg, chatbot, user_name, company_name, company_group, department, position, hire_date],
                   [msg, chatbot, response_time_output5])

    with gr.Tab("Generic OKR Virtual Assistant"):
        chatbot = gr.Chatbot()
        msg = gr.Textbox(label="Your Message")
        response_time_output6 = gr.Textbox(label="Response Time", elem_id='6')
        user_name = gr.Textbox(label="User Name")
        company_name = gr.Textbox(label="Company Name")
        company_group = gr.Textbox(label="Company Group")
        department = gr.Textbox(label="Department")
        position = gr.Textbox(label="Position")
        hire_date = gr.Textbox(label="Hire Date")

        clear = gr.ClearButton([msg, chatbot])


        def respond(message, chat_history, user_name, company_name, company_group, department, position, hire_date):
            history = []
            if len(chat_history) < 4:
                for i in range(len(chat_history)):
                    history.append(
                        {'role': 'user',
                         'content': chat_history[i][0]}
                    )
                    history.append(
                        {'role': 'assistant',
                         'content': chat_history[i][1]}
                    )

            bot_message, response_time_output = okr_chatbot(message, company_name, user_name, company_group, department,
                                                            position, hire_date, history, 4)
            chat_history.append((message, bot_message))
            time.sleep(2)
            return "", chat_history, response_time_output


        msg.submit(respond, [msg, chatbot, user_name, company_name, company_group, department, position, hire_date],
                   [msg, chatbot, response_time_output6])

    okr_button.click(improve_okr, inputs=okr_input,
                     outputs=[okr_output, response_time_output1])
    kr_button.click(improve_kr, inputs=kr_input, outputs=[kr_output, response_time_output2])

demo.launch(server_name="0.0.0.0", server_port=7863)
