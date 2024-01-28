import asyncio
import json
import copy
from fastapi import HTTPException
from openai import (AuthenticationError, APITimeoutError, BadRequestError,
                    NotFoundError, PermissionDeniedError, RateLimitError, UnprocessableEntityError, APIError)


class OpenAIHandler:
    def __init__(self, system_message_path=None, few_shot_examples_path=None, initial=True):
        if initial:
            self._semaphore = asyncio.Semaphore()
            self.system_message = system_message_path
            self.few_shot_examples = self.set_few_shot_examples(few_shot_examples_path)
            self.base_messages = self.set_base_messages()


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

    async def llm_call(self, user_text, router):
        messages = self.build_input(user_text)
        try:
            response = await router.acompletion(
                model="gpt-35-turbo",
                messages=messages,
                temperature=0.5,
                max_tokens=1000,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None)

            return response

        except AuthenticationError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except APIError as e:
            raise HTTPException(status_code=405, detail=str(e))
        except APITimeoutError as e:
            raise HTTPException(status_code=501, detail=str(e))
        except BadRequestError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except PermissionDeniedError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except RateLimitError as e:
            raise HTTPException(status_code=429, detail=str(e))
        except UnprocessableEntityError as e:
            raise HTTPException(status_code=422, detail=str(e))

    async def llm_chat(self, base_messages: list, router):

        llm_messages = copy.deepcopy(base_messages)
        llm_messages[-1]["content"] = llm_messages[-1]["content"] + " Don’t justify your answers. Obey RESTRICTIONS. Don’t give information not mentioned in the INSTRUCTIONS"

        try:
            response = await router.acompletion(
                model="gpt-35-turbo",
                messages=llm_messages,
                temperature=0.0,
                max_tokens=1000,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                stop=None)

            return response

        except AuthenticationError as e:
            raise HTTPException(status_code=401, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=429, detail=str(e))
        except APITimeoutError as e:
            raise HTTPException(status_code=501, detail=str(e))
        except BadRequestError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except PermissionDeniedError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except RateLimitError as e:
            raise HTTPException(status_code=429, detail=str(e))
        except UnprocessableEntityError as e:
            raise HTTPException(status_code=422, detail=str(e))
