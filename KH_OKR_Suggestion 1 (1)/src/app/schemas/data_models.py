from pydantic import BaseModel


class ObjectiveRequestModel(BaseModel):
    SessionID: str
    UserID: str
    UserName: str
    CompanyName: str
    CompanyGroup: str
    Department: str
    Position: str
    HireDate: str
    Objective: str
    FeedbackRate: int
    FeedbackComment: str


class ObjectiveResponseModel(BaseModel):
    SessionID: str
    NewObjectives: str = None


class KeyResultRequestModel(BaseModel):
    SessionID: str
    UserID: str
    UserName: str
    CompanyName: str
    CompanyGroup: str
    Department: str
    Position: str
    HireDate: str
    KeyResult: str
    KrZaman: bool
    KrOlculebilirlik: bool
    KrEtki: bool
    FeedbackRate: int
    FeedbackComment: str

class KeyResultResponseModel(BaseModel):
    SessionID: str
    NewKeyResult: str = None


class ChatRequestModel(BaseModel):
    SessionID: str
    UserID: str
    UserName: str
    CompanyName: str
    CompanyGroup: str
    Department: str
    Position: str
    HireDate: str
    UserMessage: str
    FeedbackRate: int
    FeedbackComment: str

class ChatResponseModel(BaseModel):
    SessionID: str
    UserID: str
    LLMAnswer: str = None
