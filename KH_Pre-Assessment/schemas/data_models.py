from pydantic import BaseModel
from typing import List


class Question(BaseModel):
    Number: str
    Subject: str
    Type: str
    Difficulty: str
    Duration: str
    Text: str
    Answer: str
    Options: List


class JobDescriptionRequestModel(BaseModel):
    JobName: str
    JobDescription: str
    QualificationName: str
    Qualifications: str


class ResponseModel(BaseModel):
    Content: List[Question]


class ApplicantRequestModel(BaseModel):
    Skills: str
    Certifications: str
    CVDescription: str

class ApplicantWithRelationRequestModel(BaseModel):
    Skills: str
    Certifications: str
    CVDescription: str
    JobPostingText: str

class ExtractSkillRequestModel(BaseModel):
    JobDescription: str

class ExtractSkillResponseModel(BaseModel):
    Skills: List[str]

class ApplicantWithSkillsRequestModel(BaseModel):
    Skills: str
    Certifications: str
    CVDescription: str
    JobSkills: List[str]

