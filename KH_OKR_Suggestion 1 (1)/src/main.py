import asyncio

from fastapi import FastAPI
from dotenv import load_dotenv
import motor.motor_asyncio
import litellm
from litellm import Router

from app.schemas.data_models import ObjectiveRequestModel, ObjectiveResponseModel, KeyResultRequestModel, \
    KeyResultResponseModel, ChatRequestModel, ChatResponseModel
from app.service.workflow import improve_objective_workflow, improve_key_result_workflow, chatbot_workflow, add_log_record, update_log_record

app = FastAPI()
load_dotenv()
client = motor.motor_asyncio.AsyncIOMotorClient(
    "mongodb+srv://okrSuggestionUser:9fXlUiHA8gqxUnvc@kocdiyalog.a0bfc.azure.mongodb.net/okrSuggestion?retryWrites=true&w=majority"
)
db = client["okrSuggestion"]
collection = db["chatHistory"]

model_list = [
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okranalytics",
        "api_key": "2507a10cc0de41cebab52d36c99a6372",
        "api_base": "https://openai-okr-analytics.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
},
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okranalytics3",
        "api_key": "a6585782500842529c8a93aa3ddf3265",
        "api_base": "https://openai-okranalytics3.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
},
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okranalytics4",
        "api_key": "4f7e016d9319417baed02079a9c230b3",
        "api_base": "https://koc-openai.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 120000,
    "rpm": 720,
},
{
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okranalytics5",
        "api_key": "f46b9456949f40d2946f315eb26b39dd",
        "api_base": "https://koc-openai-eastus.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
},
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okrsuggestion-hrsub1",
        "api_key": "a59e770b24574c6bbe2844697a2cf51c",
        "api_base": "https://openai-okrguesstion-hrsub1.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
},
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okrsuggestion-hrsub2",
        "api_key": "698ba14c504f42bb83fe59650bdcd1cc",
        "api_base": "https://openai-okrsuggestion-hrsub2.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
},
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okrsuggestion-hrsub3",
        "api_key": "a49d3014e7d340ceb451b49b574c8471",
        "api_base": "https://openai-okrsuggestion-hrsub3.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
},
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okrsuggestion-hrsub4",
        "api_key": "bd4f7348804342fdbed8ab98b4095750",
        "api_base": "https://openai-okrsuggestion-hrsub4.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
},
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okrsuggestion-hrsub5",
        "api_key": "215b313dfa1a49548a537d14024a9103",
        "api_base": "https://openai-okrsuggestion-hrsub5.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
},
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okrsuggestion-testsub1",
        "api_key": "928289f7eb794b489fb206ab5eccb462",
        "api_base": "https://openai-okrsuggestion-testsub-1.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
},
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okrsuggestion-testsub2",
        "api_key": "4415a00bc5544f8686c49c2a8c029129",
        "api_base": "https://openai-okrsuggestion-testsub-2.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
},
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okrsuggestion-testsub3",
        "api_key": "c98668f61f974d8cb2f08046731f5268",
        "api_base": "https://openai-okrsuggestion-testsub-3.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
},
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okrsuggestion-testsub4",
        "api_key": "d37071341f9341e59582a90342dd3184",
        "api_base": "https://openai-okrsuggestion-testsub-4.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
},
    {
    "model_name": "gpt-35-turbo",
    "litellm_params": { # params for litellm completion/embedding call
        "model": "azure/gpt35turbo-okrsuggestion-testsub5",
        "api_key": "9230dd6eac96451cab7f965d639a0e0f",
        "api_base": "https://openai-okrsuggestion-testsub-5.openai.azure.com/",
        "api_version": "2023-05-15"
    },
    "tpm": 240000,
    "rpm": 1440,
}
]

router = Router(model_list=model_list,
                routing_strategy="simple-shuffle")

@app.post("/improve_objective")
async def make_objective_inspiring(request_body: ObjectiveRequestModel):
    session_id = request_body.SessionID
    user_id = request_body.UserID
    user_name = request_body.UserName
    company_name = request_body.CompanyName
    company_group = request_body.CompanyGroup
    department = request_body.Department
    position = request_body.Position
    hire_date = request_body.HireDate
    old_objective_text = request_body.Objective
    feedback_rate = request_body.FeedbackRate
    feedback_comment = request_body.FeedbackComment

    if session_id == "":
        response = await improve_objective_workflow(
            old_objective_text=old_objective_text,
            router=router
        )
        total_tokens = response['usage']["total_tokens"]
        new_objective_list = response['choices'][0]['message']['content']

        session_id = await add_log_record(
            collection_object=collection,
            session_type="ImproveObjective",
            old_text=old_objective_text,
            new_text=new_objective_list,
            user_id=user_id,
            user_name=user_name,
            company_name=company_name,
            company_group=company_group,
            department=department,
            position=position,
            hire_date=hire_date,
            total_tokens=total_tokens
        )
    else:
        asyncio.create_task(update_log_record(
            collection_object=collection,
            session_id=session_id,
            feedback_rate=feedback_rate,
            feedback_comment=feedback_comment
        ))
        new_objective_list = "Feedback için teşekkürler!"

    response_data = ObjectiveResponseModel(
        SessionID=session_id,
        NewObjectives=new_objective_list
    )
    return response_data


@app.post("/improve_key_result")
async def improve_key_result_quality(request_body: KeyResultRequestModel):
    session_id = request_body.SessionID
    user_id = request_body.UserID
    user_name = request_body.UserName
    company_name = request_body.CompanyName
    company_group = request_body.CompanyGroup
    department = request_body.Department
    position = request_body.Position
    hire_date = request_body.HireDate
    old_kr_text = request_body.KeyResult
    KrZaman = request_body.KrZaman
    KrOlc = request_body.KrOlculebilirlik
    feedback_rate = request_body.FeedbackRate
    feedback_comment = request_body.FeedbackComment

    if session_id == "":
        response = await improve_key_result_workflow(
            old_kr_text=old_kr_text,
            KrZaman=KrZaman,
            KrOlculebilirlik=KrOlc,
            router=router
        )
        total_tokens = response['usage']["total_tokens"]
        new_kr_text = response['choices'][0]['message']['content']

        session_id = await add_log_record(
            collection_object=collection,
            session_type="ImproveKeyResult",
            old_text=old_kr_text,
            new_text=new_kr_text,
            user_id=user_id,
            user_name=user_name,
            company_name=company_name,
            company_group=company_group,
            department=department,
            position=position,
            hire_date=hire_date,
            total_tokens=total_tokens
        )
    else:
        asyncio.create_task(update_log_record(
            collection_object=collection,
            session_id=session_id,
            feedback_rate=feedback_rate,
            feedback_comment=feedback_comment
        ))
        new_kr_text = "Feedback için teşekkürler!"

    response_data = KeyResultResponseModel(
        SessionID=session_id,
        NewKeyResult=new_kr_text
    )
    return response_data


@app.post("/improve_objective_chat")
async def improve_objective_chat(request_body: ChatRequestModel):
    session_id = request_body.SessionID
    user_id = request_body.UserID
    user_name = request_body.UserName
    company_name = request_body.CompanyName
    company_group = request_body.CompanyGroup
    department = request_body.Department
    position = request_body.Position
    hire_date = request_body.HireDate
    user_message = request_body.UserMessage
    feedback_rate = request_body.FeedbackRate
    feedback_comment = request_body.FeedbackComment

    model_response = await chatbot_workflow(
        collection_object=collection,
        session_type="ImproveObjectiveChat",
        session_id=session_id,
        user_id=user_id,
        user_name=user_name,
        company_name=company_name,
        company_group=company_group,
        department=department,
        position=position,
        hire_date=hire_date,
        user_message=user_message,
        feedback_rate=feedback_rate,
        feedback_comment=feedback_comment,
        router=router
    )

    response_data = ChatResponseModel(
        SessionID=model_response["SessionID"],
        UserID=model_response["UserID"],
        LLMAnswer=model_response["Response"]
    )
    return response_data


@app.post("/okr_chat")
async def okr_chatbot(request_body: ChatRequestModel):
    session_id = request_body.SessionID
    user_id = request_body.UserID
    user_name = request_body.UserName
    company_name = request_body.CompanyName
    company_group = request_body.CompanyGroup
    department = request_body.Department
    position = request_body.Position
    hire_date = request_body.HireDate
    user_message = request_body.UserMessage
    feedback_rate = request_body.FeedbackRate
    feedback_comment = request_body.FeedbackComment

    model_response = await chatbot_workflow(
        collection_object=collection,
        session_type="OKRFreeChat",
        session_id=session_id,
        user_id=user_id,
        user_name=user_name,
        company_name=company_name,
        company_group=company_group,
        department=department,
        position=position,
        hire_date=hire_date,
        user_message=user_message,
        feedback_rate=feedback_rate,
        feedback_comment=feedback_comment,
        router=router
    )

    response_data = ChatResponseModel(
        SessionID=model_response["SessionID"],
        UserID=model_response["UserID"],
        LLMAnswer=model_response["Response"]
    )
    return response_data


@app.post("/okr_suggestion_chat")
async def okr_kr_suggestion_chatbot(request_body: ChatRequestModel):
    session_id = request_body.SessionID
    user_id = request_body.UserID
    user_name = request_body.UserName
    company_name = request_body.CompanyName
    company_group = request_body.CompanyGroup
    department = request_body.Department
    position = request_body.Position
    hire_date = request_body.HireDate
    user_message = request_body.UserMessage
    feedback_rate = request_body.FeedbackRate
    feedback_comment = request_body.FeedbackComment

    model_response = await chatbot_workflow(
        collection_object=collection,
        session_type="OKRSuggestion",
        session_id=session_id,
        user_id=user_id,
        user_name=user_name,
        company_name=company_name,
        company_group=company_group,
        department=department,
        position=position,
        hire_date=hire_date,
        user_message=user_message,
        feedback_rate=feedback_rate,
        feedback_comment=feedback_comment,
        router=router
    )

    response_data = ChatResponseModel(
        SessionID=model_response["SessionID"],
        UserID=model_response["UserID"],
        LLMAnswer=model_response["Response"]
    )
    return response_data


@app.post("/development_kr_suggestion_chat")
async def development_kr_suggestion_chatbot(request_body: ChatRequestModel):
    session_id = request_body.SessionID
    user_id = request_body.UserID
    user_name = request_body.UserName
    company_name = request_body.CompanyName
    company_group = request_body.CompanyGroup
    department = request_body.Department
    position = request_body.Position
    hire_date = request_body.HireDate
    user_message = request_body.UserMessage
    feedback_rate = request_body.FeedbackRate
    feedback_comment = request_body.FeedbackComment

    model_response = await chatbot_workflow(
        collection_object=collection,
        session_type="DevelopmentKRSuggestion",
        session_id=session_id,
        user_id=user_id,
        user_name=user_name,
        company_name=company_name,
        company_group=company_group,
        department=department,
        position=position,
        hire_date=hire_date,
        user_message=user_message,
        feedback_rate=feedback_rate,
        feedback_comment=feedback_comment,
        router=router
    )

    response_data = ChatResponseModel(
        SessionID=model_response["SessionID"],
        UserID=model_response["UserID"],
        LLMAnswer=model_response["Response"]
    )
    return response_data


@app.post("/aligned_okr_suggestion_chat")
async def aligned_okr_suggestion_chatbot(request_body: ChatRequestModel):
    session_id = request_body.SessionID
    user_id = request_body.UserID
    user_name = request_body.UserName
    company_name = request_body.CompanyName
    company_group = request_body.CompanyGroup
    department = request_body.Department
    position = request_body.Position
    hire_date = request_body.HireDate
    user_message = request_body.UserMessage
    feedback_rate = request_body.FeedbackRate
    feedback_comment = request_body.FeedbackComment

    model_response = await chatbot_workflow(
        collection_object=collection,
        session_type="AlignedOKRSuggestion",
        session_id=session_id,
        user_id=user_id,
        user_name=user_name,
        company_name=company_name,
        company_group=company_group,
        department=department,
        position=position,
        hire_date=hire_date,
        user_message=user_message,
        feedback_rate=feedback_rate,
        feedback_comment=feedback_comment,
        router=router
    )

    response_data = ChatResponseModel(
        SessionID=model_response["SessionID"],
        UserID=model_response["UserID"],
        LLMAnswer=model_response["Response"]
    )
    return response_data
