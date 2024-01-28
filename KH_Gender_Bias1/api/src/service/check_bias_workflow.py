import asyncio
import json

from src.integrations.llm import OpenAIHandler
from src.utils import get_logger
from src import constants
from .exceptions import LLMExtractionError
from .callbacks import task_done_callback
from .processing import preprocess

logger = get_logger(__name__)


async def extract_keywords(sentence: str, handler: OpenAIHandler) -> dict:
    response = await handler.generate_response_extraction(sentence)
    response = json.loads(response.model_dump_json())
    response = response['choices'][0]['message']['content']
    response = json.loads(response)
    if response:
        logger.debug(f"The extracted phrases from sentence {sentence}: {response}")
    return response


async def if_used_for_person(response: dict, handler: OpenAIHandler, sentence: str) -> dict:
    combined_dict = {}
    for key, value in response.items():
        if value:
            if isinstance(value, str):
                flag = await handler.generate_response_person(sentence, value, key)
                flag = json.loads(flag.model_dump_json())
                flag = flag['choices'][0]['message']['content']
                logger.info(f"Person flag for the sentence '{sentence}' and value '{value}' is {flag}")
                if flag.lower() == "yes":
                    combined_dict[key] = value

            elif isinstance(value, list):
                combined_dict[key] = value
                for val in value:
                    flag = await handler.generate_response_person(sentence, val, key)
                    flag = json.loads(flag.model_dump_json())
                    flag = flag['choices'][0]['message']['content']
                    logger.info(f"Person flag for the sentence '{sentence}' and value '{val}' is {flag}")
                    if flag.lower() == "no":
                        combined_dict[key].remove(val)
    return combined_dict


async def chain(handler: OpenAIHandler, sentence: str):
    extraction_response = await extract_keywords(sentence, handler)
    filtered_dict = {k: v for k, v in extraction_response.items() if v != ''}
    if filtered_dict:
        person_response = await if_used_for_person(filtered_dict, handler, sentence)
        return person_response
    else:
        raise LLMExtractionError(sentence)


async def check_bias_workflow(raw_text: str):
    handler = OpenAIHandler(excel_path=constants.EXCEL_PATH,
                            system_message_path=constants.SYSTEM_MESSAGE_PATH,
                            few_shot_examples_path=constants.FEW_SHOT_EXAMPLES_PATH)

    clean_sentences = await preprocess(raw_text)

    tasks = []
    results = []
    for sentence in clean_sentences:
        task = asyncio.create_task(chain(handler, sentence))
        task.add_done_callback(lambda x: task_done_callback(x, logger, results))
        tasks.append(task)

    await asyncio.gather(*tasks, return_exceptions=True)
    logger.debug(results)
    return results
