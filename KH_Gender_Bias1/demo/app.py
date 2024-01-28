import requests
import json

import pandas as pd
from openai import AzureOpenAI
import gradio as gr

GENERATIVE_PROMPT = """
Assistant is an intelligent system that detect discriminatory phrases/expressions present in job posting texts.
Instructions:
- The discriminatory words can be used but not limited to when describing the role or responsibilities of a candidate.
- The discrimination can be based on gender, age, marital status, military status, etc.
- Return your answer where you detected discriminatory language.
"""

CLIENT = AzureOpenAI(
    api_key="f46b9456949f40d2946f315eb26b39dd",
    azure_endpoint="https://koc-openai-eastus.openai.azure.com/",
    api_version="2023-07-01-preview"
)


def generate_generative_response(input_text):
    response = CLIENT.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system",
                   "content": GENERATIVE_PROMPT},
                  {"role": "user",
                   "content": input_text}],
        temperature=0,
        max_tokens=1000,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None)

    response = response.model_dump()
    return response['choices'][0]['message']['content']


def check_bias_in_job_posting(input_text: str):
    params = {
        "ILAN_ID": "96B889AE-CFDC-497B-920A-970FF861C6D4",
        "KULLANICI_ID": "48D689C9-7A92-436D-3D48-08D9DAD35B22",
        "ROL_SORUMLULUK_BASLIK": ";",
        "ROL_SORUMLULUK_METIN": "",
        "ARANILAN_NITELIKLER_BASLIK": "",
        "ARANILAN_NITELIKLER_METIN": input_text,
        "ILETILME_TARIH": "2023-10-10 09:05:45.7095874"
    }
    response = requests.post('http://localhost:5000/check_bias/', json=params).json()

    df = pd.DataFrame(
        columns=['Ayrımcı Dil İçeren İfade', 'Ayrımcı Dil İçeren Kısım', 'Yerine Kullanılması Gereken Kelime'])
    df['Ayrımcı Dil İçeren İfade'] = [resp['AYRIMCI_IFADE'] for resp in response['AYRIMCI_IFADELER']]
    df['Ayrımcı Dil İçeren Kısım'] = [resp['AYRIMCI_KISIM'] for resp in response['AYRIMCI_IFADELER']]
    df['Yerine Kullanılması Gereken Kelime'] = [resp['AYRIMCI_IFADE_ONERI'] for resp in response['AYRIMCI_IFADELER']]

    return df, response


def predict_gender(name):
    gender_params = {
        "BASVURU_ID": "51D8C7A1-6BCE-4E9A-E2D7-08DBC94B4A21",
        "BASVURAN_AD": name
    }

    response = requests.post('http://localhost:5000/predict_gender/', json=gender_params)
    return response.json()


with gr.Blocks() as demo:
    gr.Markdown("""
    # KoçDigital - KH Ayrımcı Dil Demo 🚀‍👩‍🚀👨‍🏫
    İş ilanlarındaki ayrımcı dil içeren ifadeleri görün ve doğru kullanımları ile değiştirin!
    """)

    with gr.Tab("Sözlük Destekli GPT-4 Çözümü"):
        text_input = gr.Textbox(lines=5, label="Job Posting Text")
        sozluk_button = gr.Button("Submit")
        df_output = gr.Dataframe()
        endpoint_output = gr.Json(label="Response Body")

    with gr.Tab("Generative GPT-4 Çözümü"):
        text_input_generative = gr.Textbox(lines=5, label="Job Posting Text")
        generative_button = gr.Button("Submit")
        model_output = gr.Textbox(label="Generative Response")

    with gr.Tab("İsimden Cinsiyet Tahminleme"):
        name_input = gr.Textbox(label="Applicant Name")
        gender_button = gr.Button("Submit")
        gender_prediction = gr.Json(label="Response Body")

    gender_button.click(predict_gender, inputs=name_input, outputs=gender_prediction)
    sozluk_button.click(check_bias_in_job_posting, inputs=text_input, outputs=[df_output, endpoint_output])
    generative_button.click(generate_generative_response, inputs=text_input_generative, outputs=model_output)

demo.launch(server_name="0.0.0.0", server_port=7862)
