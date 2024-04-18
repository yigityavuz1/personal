import random
from templates import alpaca_prompt_input_tr, alpaca_prompt_no_input_tr
from system_prompts import system_prompts_tr
from dataset.base import BaseDataset


class AlpacaGPT4TurkishDataset(BaseDataset):
    def __init__(self, path, local):
        super().__init__(path, local)

    @staticmethod
    def map_to_chat_template(examples):

        instructions = examples["instruction-turkish"]
        inputs = examples["input-turkish"]
        outputs = examples["output-turkish"]
        texts = []
        for instruction, input, output in zip(instructions, inputs, outputs):
            conv = []
            system_prompt = random.choice(system_prompts_tr)
            if input == "" or input is None:
                template = random.choice(alpaca_prompt_no_input_tr)
                text = template.format(system_prompt, instruction)
            else:
                template = random.choice(alpaca_prompt_input_tr)
                text = template.format(system_prompt, instruction, input)

            if system_prompt == "":
                text = text.strip()
            conv.append({'role': 'user', 'content': text})
            conv.append({'role': 'assistant', 'content': output})
            # print(conv)

            texts.append(conv)
        return {"conversation": texts, }
