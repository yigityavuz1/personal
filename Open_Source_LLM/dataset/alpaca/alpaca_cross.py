import random

from datasets import load_dataset

from system_prompts import system_prompts_en, system_prompts_en_tr, system_prompts_tr_en
from templates import alpaca_prompt_input_tr, alpaca_prompt_no_input_tr, alpaca_prompt_input_en, \
    alpaca_prompt_no_input_en
from utils import set_environment, set_logging
from dataset.base import BaseDataset

set_environment()
set_logging()


class AlpacaGPT4CrossDataset(BaseDataset):
    def __init__(self, path, local):
        super().__init__(path, local)

    @staticmethod
    def map_to_chat_template(examples):

        instructions_en = examples["instruction"]
        inputs_en = examples["input"]
        outputs_en = examples["output"]
        instructions_tr = examples["instruction-turkish"]
        inputs_tr = examples["input-turkish"]
        outputs_tr = examples["output-turkish"]
        texts = []
        for ins_en, in_en, o_en, ins_tr, in_tr, o_tr in zip(instructions_en, inputs_en, outputs_en, instructions_tr,
                                                            inputs_tr, outputs_tr):
            conv = []
            choice = random.choice([0, 1, 2])
            if choice == 0:
                system_prompt = random.choice(system_prompts_en)
                if in_en == "" or in_en is None:
                    template = random.choice(alpaca_prompt_no_input_en)
                    text = template.format(system_prompt, ins_en)
                else:
                    template = random.choice(alpaca_prompt_input_en)
                    text = template.format(system_prompt, ins_en, in_en)

                if system_prompt == "":
                    text = text.strip()
                output = o_en
            elif choice == 1:
                system_prompt = random.choice(system_prompts_en_tr)
                if in_en == "" or in_en is None:
                    template = random.choice(alpaca_prompt_no_input_en)
                    text = template.format(system_prompt, ins_en)
                else:
                    template = random.choice(alpaca_prompt_input_en)
                    text = template.format(system_prompt, ins_en, in_en)

                if system_prompt == "":
                    text = text.strip()
                output = o_tr
            else:
                system_prompt = random.choice(system_prompts_tr_en)
                if in_tr == "" or in_tr is None:
                    template = random.choice(alpaca_prompt_no_input_tr)
                    text = template.format(system_prompt, ins_tr)
                else:
                    template = random.choice(alpaca_prompt_input_tr)
                    text = template.format(system_prompt, ins_tr, in_tr)

                if system_prompt == "":
                    text = text.strip()
                output = o_en

            conv.append({'role': 'user', 'content': text})
            conv.append({'role': 'assistant', 'content': output})
            # print(conv)

            texts.append(conv)
        return {"conversation": texts, }

