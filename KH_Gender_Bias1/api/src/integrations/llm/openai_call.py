import asyncio
import json
import copy

import pandas as pd
import textdistance
from openai import AsyncAzureOpenAI

from src.constants import PERSON_FEW_SHOT_EXAMPLES_PATH

class OpenAIHandler:
    def __init__(self, system_message_path=None, few_shot_examples_path=None, excel_path=None):
        self._semaphore = asyncio.Semaphore()
        self.excel_file = self.set_excel_file(excel_path)
        self.system_message = self.set_system_message(system_message_path)
        self.few_shot_examples = self.set_few_shot_examples(few_shot_examples_path)
        self.base_messages = self.set_base_messages()
        self.keywords = self.set_keywords()
        self.client = AsyncAzureOpenAI()

    def set_excel_file(self, excel_path):
        with pd.ExcelFile(excel_path) as xls:
            full_data = pd.read_excel(xls)
            columns = ['İş İlanı', 'İş ilanı']
            filtered_df = full_data[full_data['Kullanım Alanı'].isin(columns)]
        return filtered_df

    def set_system_message(self, system_message_path: str) -> str:
        with open(system_message_path, 'r') as f:
            system_message = f.read()

        return system_message

    def set_keywords(self) -> list:
        all_keywords = [i.strip() for i in self.excel_file['Ayrımcı Dil İçeren Kelime'].values.tolist()]
        return all_keywords

    def set_few_shot_examples(self, few_shot_examples_path: str) -> dict:
        if few_shot_examples_path:
            with open(few_shot_examples_path, 'r') as f:
                few_shot_examples = f.read()

            few_shot_examples = json.loads(few_shot_examples)
            return few_shot_examples
        else:
            return None

    def set_base_messages(self) -> list:
        messages = [
            {"role": "system",
             "content": self.system_message},
        ]

        if self.few_shot_examples:
            messages.extend(self.few_shot_examples)
        return messages

    def build_input(self, input_text: str) -> list:
        base_messages = copy.deepcopy(self.base_messages)

        base_messages.append(
            {"role": "user",
             "content": input_text}
        )
        return base_messages

    def my_sim(self, key, content):
        content = content.lower()
        f1 = textdistance.LCSStr()
        score = f1.similarity(key, content)
        return score, len(key), score / len(key)

    def find_keywords(self, text):
        return [key for key in self.keywords if self.my_sim(key, text)[2] > 0.80]

    def customized_few_shot_examples(self, keyword: str) -> list:
        row = self.excel_file.loc[self.excel_file['Ayrımcı Dil İçeren Kelime'] == keyword]
        custom_few_shots = []
        if not pd.isna(row['few-shot örnek 1 (ayrımcı gelmeyecek)'].values[0]):
            custom_few_shots.append({
                "role": "user",
                "content": row['few-shot örnek 1 (ayrımcı gelmeyecek)'].values[0].strip()
            })
            custom_few_shots.append({
                "role": "assistant",
                "content": "No"
            })

        if not pd.isna(row['few-shot örnek 2 (ayrımcı)'].values[0]):
            custom_few_shots.append({
                "role": "user",
                "content": "Sentence:" + row['few-shot örnek 2 (ayrımcı)'].values[0].strip() + "\nWord:" + keyword + '\n'
            })
            custom_few_shots.append({
                "role": "assistant",
                "content": "Yes"
            })
        return custom_few_shots

    async def generate_response_extraction(self, job_text):
        keyword_list = self.find_keywords(job_text)
        input_text = "Text: {text}\nKeywords: {lst}".format(text=job_text, lst=keyword_list)
        messages = self.build_input(input_text)
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0,
            max_tokens=100,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None)

        return response

    async def generate_response_person(self, sentence, chunk, keyword):
        input_text = (
            """Sentence: '{sentence}' 
           Part: '{chunk}'
           Word: '{keyword}"""
            .format(sentence=sentence, chunk=chunk, keyword=keyword))

        messages = [{"role": "system",
                     "content": "You will be given a sentence, a part of the sentence and a word. Your job is to determine whether or not that word in the sentence in the corresponding part is used towards a person or not. Either answer with 'Yes' or 'No'"}]
        if self.customized_few_shot_examples(keyword):
            messages.extend(self.customized_few_shot_examples(keyword))
        else:
            messages.extend(self.set_few_shot_examples(PERSON_FEW_SHOT_EXAMPLES_PATH))
        messages.append({"role": "user",
                         "content": input_text})

        print(messages)
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0,
            max_tokens=10,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None)

        return response
