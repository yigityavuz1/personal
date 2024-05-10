from pydantic import BaseModel
from typing import List

class QuestionRequestModel(BaseModel):
    Number : str
    text : str
    Type: str
    Difficulty: str
    ideal_answer : str
    user_answer : str

class QuestionEvaluationModel(BaseModel):
    Number : str
    text : str

class ResponseModel(BaseModel):
    Evaluations : List[QuestionEvaluationModel]



