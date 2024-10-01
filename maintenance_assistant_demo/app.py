from typing import Union
from fastapi import FastAPI,HTTPException
import uvicorn
from entek_api import make_query
import schemas as _schemas
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    return {"KD bakım asistanı botuna hoşgeldiniz..."}

@app.post("/api/ask_question")
async def ask_question(request_body:_schemas.RequestBody):
    print("Request Body",request_body)
    result=await make_query(request_body)
    print("Result",result)
    return result

