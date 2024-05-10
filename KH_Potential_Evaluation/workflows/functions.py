import logging
from openai import AsyncAzureOpenAI
import re
import json
from abc import ABC, abstractmethod

score_mappings = {
    "Easy": {
        "True or False": "4",
    },
    "Normal": {
        "Open Ended": "10",
        "Multiple Choice": "9"
    },
    "Hard": {
        "Open Ended": "15",
    }
}
class AbstractEvaluateAnswer(ABC):
    @abstractmethod
    def get_openai_response(self, question, ideal_answer, user_answer):
        pass


class AbstractAsyncAzureOpenAI(ABC):
    @abstractmethod
    def define_client(self):
        pass

class EvaluateAnswer(AbstractEvaluateAnswer):
    def __init__(self, config, static, client = None):
        self.config = config
        self.static = static

    
    async def get_openai_response(self, question, ideal_answer, user_answer):
        self.client_init = AsyncOpenAIClient(self.config)
        self.client = self.client_init.define_client() 
        prompt = self.static.PROMPT.format(question=question, ideal_answer=ideal_answer, user_answer=user_answer)
        message_text = [{"role":"system","content":prompt},{"role":"user","content":"Score the user's answer out of 10 and give explanation."}]
        try:
            completion = await self.client.chat.completions.create(
                model=self.config['openai_endpoints']['model_name'],
                messages = message_text,
                temperature=0.7,
                max_tokens=800,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None
            )
            return completion.choices[0].message.content
        except Exception as e:
            return {"error": str(e)}
        

    

class AsyncOpenAIClient(AbstractAsyncAzureOpenAI):
    '''
    OpenAIClient class to define the OpenAI client
    returns the async client and model name
    '''
    def __init__(self, config):
        self.config = config

    def define_client(self):
        client = AsyncAzureOpenAI(
            azure_endpoint=self.config["openai_endpoints"]["api_base"],
            api_key=self.config["openai_endpoints"]["api_key"],
            api_version=self.config["openai_endpoints"]["api_version"]
        )
        return client

async def get_openai_response(config, question, ideal_answer, user_answer,prompt,Difficulty,Type):
    client = AsyncAzureOpenAI(
            azure_endpoint=config["openai_endpoints"]["api_base"],
            api_key=config["openai_endpoints"]["api_key"],
            api_version=config["openai_endpoints"]["api_version"]
        )
    prompt = prompt.format(question=question, ideal_answer=ideal_answer, user_answer=user_answer)
    message_text = [{"role":"system","content":prompt},{"role":"user","content":"Score the user's answer out of 10 and give explanation."}]
    try:
        completion = await client.chat.completions.create(
            model="gpt4turbo-okrsuggestion-hrsub5",
            messages = message_text,
            temperature=0.7,
            max_tokens=800,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            response_format = {'type': 'json_object'}
        )
        json_text = json.loads(completion.choices[0].message.content)
        coeffiecient = score_mappings[Difficulty][Type]
        net_score = (int(json_text["Score"]) * int(coeffiecient)) / 10
        json_text["net_score"] = net_score
        return str(json_text)
    except Exception as e:
        return {"error": str(e)}