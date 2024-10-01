import pydantic as _pydantic
from typing import List, Optional
import datetime

class History(_pydantic.BaseModel):
    role:str
    content:str

class RequestBody(_pydantic.BaseModel):
    question: str
    history:List[History]

class ChatUserFeedback(_pydantic.BaseModel):
    chatSessionId:str
    userId:str
    userDisplayName:str
    timestamp:datetime.datetime
    userSatisfied:bool
    userComment:str

class ChatActivityLog(_pydantic.BaseModel):
    chatSessionId:str
    userId:str
    userDisplayName:str
    timestamp:datetime.datetime
    logType:str
    message:str
    resourceType:str
    resourceName:str
    resourceUrl:str

class ChatAnalyticsReport(_pydantic.BaseModel):
    chatSessionId:str
    userId:str
    userDisplayName:str
    timestamp:datetime.datetime
    chatStartedAt:datetime.datetime
    chatEndedAt:datetime.datetime
    chatDuration:int
    history:str
    totalMessageCount:int
    userMessageCount:int
    assistantMessageCount:int
    totalResourceCount:int
    pdfCount:int
    pdfsShared:str
    imageCount:int
    imagesShared:str
    reftableCount:int
    reftablesShared:str
