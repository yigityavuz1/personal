from pydantic import BaseModel

class RequestModel(BaseModel):
    text: str
    sessionID: str
    cart: list[dict]

class ResponseModel(BaseModel):
    basket: list[str]
    messages: list[dict[str, str]]