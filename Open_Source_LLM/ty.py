from utils import set_environment, set_logging
set_environment()
set_logging()

from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


model_id = "Trendyol/Trendyol-LLM-7b-chat-dpo-v1.0"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id,
                                             device_map='auto',
                                             load_in_8bit=True)

sampling_params = dict(do_sample=True, temperature=0.3, top_k=50, top_p=0.9)

pipe = pipeline("text-generation",
                model=model,
                tokenizer=tokenizer,
                device_map="auto",
                max_new_tokens=1024,
                return_full_text=True,
                repetition_penalty=1.1
               )

DEFAULT_SYSTEM_PROMPT = "Sen yardımcı bir asistansın ve sana verilen talimatlar doğrultusunda en iyi cevabı üretmeye çalışacaksın.\n"

TEMPLATE = (
    "[INST] {system_prompt}\n\n"
    "{instruction} [/INST]"
)

def generate_prompt(instruction, system_prompt=DEFAULT_SYSTEM_PROMPT):
    return TEMPLATE.format_map({'instruction': instruction,'system_prompt': system_prompt})

def generate_output(user_query, sys_prompt=DEFAULT_SYSTEM_PROMPT):
    prompt = generate_prompt(user_query, sys_prompt)
    outputs = pipe(prompt,
               **sampling_params
              )
    return outputs[0]["generated_text"].split("[/INST]")[-1]

user_query = "şu cümlenin gramerini düzenle 'Kastamonu'da seyir halindeki otomobil yandı'"
response = generate_output(user_query)
print(response)

import pandas as pd

d = pd.read_json("data/okr_ner_etiketli_ver/bireysel3.jsonl")
with open("data/okr_ner_etiketli_ver/kolektif1.jsonl", "r") as f:
    data = f.readlines()

print(data[0])