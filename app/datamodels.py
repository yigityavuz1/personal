from pydantic import BaseModel

class JobPosting(BaseModel):
    job_posting_id: str
    job_posting_text: str

class JobPostingUpdateResponse(BaseModel):
    message: str

class JobPostingSearchResponse(BaseModel):
    job_posting_id: str
    job_posting_text: str
