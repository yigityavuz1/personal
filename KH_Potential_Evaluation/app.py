from fastapi import FastAPI
import logging
from yaml import safe_load
from schemas.data_models import ResponseModel, QuestionRequestModel, QuestionEvaluationModel
from workflows.functions import EvaluateAnswer, AsyncOpenAIClient, get_openai_response
import static.prompt

with open("config.yaml") as file:
    config = safe_load(file)

app = FastAPI()

@app.post("/evaluate")
async def evaluate(
    requestbody: QuestionRequestModel
):
    return_answer = await get_openai_response(config,question=requestbody.text, ideal_answer=requestbody.ideal_answer, user_answer=requestbody.user_answer,prompt=static.prompt.PROMPT,Difficulty=requestbody.Difficulty,Type=requestbody.Type)
    

    return return_answer

