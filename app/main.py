from fastapi import FastAPI, HTTPException
from app.datamodels import JobPosting, JobPostingUpdateResponse, JobPostingSearchResponse
from app.db import MongoDBClient
from app.embedding_service import EmbeddingService
import numpy as np

app = FastAPI()

db_client = MongoDBClient()
embedding_service = EmbeddingService()

@app.post("/update", response_model=JobPostingUpdateResponse)
async def update_job_posting(job_posting: JobPosting):
    try:
        # Create embedding for the job posting text
        embedding = embedding_service.create_embedding(job_posting.job_posting_text)
        # Insert job posting data into MongoDB
        db_client.insert_job_posting(job_posting.job_posting_id, embedding.tolist(), job_posting.job_posting_text)
        return JobPostingUpdateResponse(message="Job posting is updated.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", response_model=JobPostingSearchResponse)
async def search_job_posting(job_posting: JobPosting):
    """
    Endpoint to search for similar job postings based on text similarity.
    
    This endpoint creates an embedding for the provided job posting text,
    performs a vector similarity search using the embedding, and returns
    the most similar job posting found in the MongoDB collection.
    
    :param job_posting: JobPosting - The job posting details (ID and text).
    :return: JobPostingSearchResponse - The most similar job posting found.
    """
    try:
        # Create embedding for the search text
        embedding = embedding_service.create_embedding(job_posting.job_posting_text)
        # Search for the closest job posting
        results = db_client.find_similar_job_posting(embedding.tolist(), num_candidates=10, limit=1)
        if not results:
            raise HTTPException(status_code=404, detail="Job posting not found")
        # Get the most similar job posting
        closest_posting = results[0]
        return JobPostingSearchResponse(
            job_posting_id=closest_posting["job_posting_id"],
            job_posting_text=closest_posting["job_posting_text"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
