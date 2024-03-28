from fastapi import FastAPI
import logging
from yaml import safe_load

from schemas.data_models import JobDescriptionRequestModel, ApplicantRequestModel, ResponseModel, ApplicantWithRelationRequestModel, ExtractSkillRequestModel, ExtractSkillResponseModel, ApplicantWithSkillsRequestModel
import static.prompts
from workflows.functions import get_questions,get_as_json, get_skills

with open("config.yaml", "r") as file:
    config = safe_load(file)

app = FastAPI()


@app.post("/from_job_description")
async def from_job_description(
        request_body: JobDescriptionRequestModel
):
    logging.info("Starting to process the request...")
    prompt = static.prompts.JOB_PROMPT
    user_request = static.prompts.JOB_DIFFICULTIES.format(
        job_desc=request_body.JobDescription,
        qualifications=request_body.Qualifications
    )
    logging.info("User request is formatted!")
    question_list = await get_as_json(
        config=config,
        prompt=prompt,
        user_request=user_request
    )

    response = ResponseModel(
        Content=question_list
    )
    logging.info("Request is processed!")
    return response


@app.post("/from_applicant")
async def from_applicant(
        request_body: ApplicantRequestModel
):
    prompt = static.prompts.CV_PROMPT
    user_request = static.prompts.CV_DIFFICULTIES.format(
        skills=request_body.Skills,
        certificates=request_body.Certifications,
        cv_desc=request_body.CVDescription
    )
    question_list = await get_as_json(
        config=config,
        prompt=prompt,
        user_request=user_request
    )

    response = ResponseModel(
        Content=question_list
    )
    return response

@app.post("/from_applicant_with_jobtext")
async def from_applicant_with_relation(
    request_body: ApplicantWithRelationRequestModel
):
    prompt_extraction = static.prompts.SKILL_EXTRACTION
    user_request_extraction = static.prompts.SKILL_EXTRACTION_INPUT.format(job_posting_text = request_body.JobPostingText)
    extracted_skills = await get_skills(
        config=config,
        prompt=prompt_extraction,
        user_request=user_request_extraction
    )
    prompt = static.prompts.CV_PROMPT_RELATION
    user_request = static.prompts.CV_DIFFICULTIES_RELATION.format(
        job_posting_skills=str(extracted_skills),
        candidate_skills=request_body.Skills,
        certificates=request_body.Certifications,
        cv_desc=request_body.CVDescription
    )
    question_list = await get_as_json(
        config=config,
        prompt=prompt,
        user_request=user_request
    )

    response = ResponseModel(
        Content=question_list
    )
    return response


@app.post('/extract_skills')
async def extract_skills(
    request_body: ExtractSkillRequestModel
):
    prompt = static.prompts.SKILL_EXTRACTION
    user_request = static.prompts.SKILL_EXTRACTION_INPUT.format(job_posting_text = request_body.JobDescription)
    extracted_skills = await get_skills(
        config=config,
        prompt=prompt,
        user_request=user_request
    )

    response = ExtractSkillResponseModel(
        Skills=extracted_skills
    )
    return response

@app.post('/from_applicant_with_skills')
async def from_applicant_with_skills(
    request_body: ApplicantWithSkillsRequestModel
):
    prompt = static.prompts.CV_PROMPT_RELATION
    user_request = static.prompts.CV_DIFFICULTIES_RELATION.format(
        job_posting_skills=request_body.JobSkills,
        candidate_skills=request_body.Skills,
        certificates=request_body.Certifications,
        cv_desc=request_body.CVDescription
    )
    question_list = await get_as_json(
        config=config,
        prompt=prompt,
        user_request=user_request
    )

    response = ResponseModel(
        Content=question_list
    )
    return response
