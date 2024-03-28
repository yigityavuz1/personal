import logging
from openai import AsyncAzureOpenAI
import re
import json

from schemas.data_models import Question


async def get_questions(
        config,
        prompt,
        user_request
):
    duration_mappings = {
    "Easy": {
        "Open Ended": "180",
        "True or False": "45",
        "Multiple Choice": "120"
    },
    "Normal": {
        "Open Ended": "300",
        "True or False": "60",
        "Multiple Choice": "180"
    },
    "Hard": {
        "Open Ended": "420",
        "True or False": "120",
        "Multiple Choice": "240"
    }
    }
    message_text = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_request}
        ]
    client = AsyncAzureOpenAI(
        azure_endpoint=config["openai_endpoints"]["api_base"],
        api_key=config["openai_endpoints"]["api_key"],
        api_version=config["openai_endpoints"]["api_version"]
    )
    logging.info("Message text is being sent to OpenAI...")
    completion = await client.chat.completions.create(
        model="gpt4-1106-kh",
        messages=message_text,
        temperature=0.7,
        max_tokens=2000,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None
    )
    logging.info("Response text is received from OpenAI!")

    logging.info("Required parts are being extracted from response text...")
    question_list = []
    question_block_pattern = r'\((.*?)\) \((.*?)\) \((.*?)\) \((.*?)\) - Question (\d+): ([\s\S]*?)(?=(-|\d+\.) \((.*?)\) \((.*?)\) \((.*?)\) \((.*?)\)|Answers)'
    answer_block_pattern = r'Answer for Question \d+:[\s\n]([\s+\S+]*?)(?=(-|\d+\.)|$)'
    full_text = completion.choices[0].message.content
    questions = re.findall(question_block_pattern, full_text, re.MULTILINE)
    answers = re.findall(answer_block_pattern, full_text)
    logging.info("Required parts are extracted from response text!")

    logging.info("Question list is being prepared...")
    for question, answer in zip(questions, answers):
        topic = question[0]
        question_type = question[1]
        difficulty = question[2]
        duration = duration_mappings[difficulty][question_type]
        number = question[4]
        text = question[5]
        answer = answer[0]

        question = Question(
            Number=number,
            Subject=topic,
            Type=question_type,
            Difficulty=difficulty,
            Duration=duration,
            Text=text,
            Answer=answer
        )
        question_list.append(question)
    logging.info("Question list is created!")

    return question_list

async def get_as_json(
        config,
        prompt,
        user_request
) -> list:
    duration_mappings = {
    "Easy": {
        "Open Ended": "180",
        "True or False": "45",
        "Multiple Choice": "120"
    },
    "Normal": {
        "Open Ended": "300",
        "True or False": "60",
        "Multiple Choice": "180"
    },
    "Hard": {
        "Open Ended": "420",
        "True or False": "120",
        "Multiple Choice": "240"
    }
    }
    message_text = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_request}
        ]
    client = AsyncAzureOpenAI(
        azure_endpoint=config["openai_endpoints"]["api_base"],
        api_key=config["openai_endpoints"]["api_key"],
        api_version=config["openai_endpoints"]["api_version"]
    )

    completion = await client.chat.completions.create(
        model="gpt4turbo-okrsuggestion-hrsub5",
        messages=message_text,
        temperature=0.7,
        max_tokens=2000,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        response_format = {"type":"json_object"}
    )
    full_json = completion.choices[0].message.content
    full_json = json.loads(full_json)
    question_list = []
    for question in full_json['questions_response']:
        difficulty = question["Difficulty"]
        question_type = question["Type"]
        duration = duration_mappings.get(difficulty, {}).get(question_type)
        question["Duration"] = duration
    #add duration by using duration mapping to json
        question_model = Question(
            Number=str(question['Number']),
            Subject=question['Subject'],
            Type=question['Type'],
            Difficulty=question['Difficulty'],
            Duration=question['Duration'],
            Text=question['Text'],
            Answer=question['Answer'],
            Options=question['Options']
        )
        question_list.append(question_model)
    return question_list



def add_duration_to_questions(json_obj):
    duration_mappings = {
    "Easy": {
        "Open Ended": "180",
        "True or False": "45",
        "Multiple Choice": "120"
    },
    "Normal": {
        "Open Ended": "300",
        "True or False": "60",
        "Multiple Choice": "180"
    },
    "Hard": {
        "Open Ended": "420",
        "True or False": "120",
        "Multiple Choice": "240"
    }
    }

    # Parse the JSON object
    questions = json.loads(json_obj)

    # Add duration to each question
    for question in questions:
        difficulty = question["difficulty"]
        question_type = question["type"]
        duration = duration_mappings.get(difficulty, {}).get(question_type)
        question["duration"] = duration

    return questions


async def get_skills(
        config,
        prompt,
        user_request
):
    message_text = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_request}
    ]
    client = AsyncAzureOpenAI(
        azure_endpoint=config["openai_endpoints"]["api_base"],
        api_key=config["openai_endpoints"]["api_key"],
        api_version=config["openai_endpoints"]["api_version"]
    )
    completion = await client.chat.completions.create(
        model="gpt4turbo-okrsuggestion-hrsub5",
        messages=message_text,
        temperature=0.7,
        max_tokens=2000,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        response_format = {"type":"json_object"}

    )
    full_text = completion.choices[0].message.content
    full_json = json.loads(full_text)
    return full_json["hard_skills"]