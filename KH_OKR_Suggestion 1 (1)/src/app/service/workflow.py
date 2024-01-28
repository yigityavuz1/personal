import asyncio
import copy
import datetime
import json
from bson.objectid import ObjectId
from urllib.parse import unquote

from app.integrations.llm import OpenAIHandler
from app.utils import get_logger
from app.static import constants

logger = get_logger(__name__)


async def add_log_record(
        collection_object,
        session_type: str,
        old_text: str,
        new_text: str,
        user_id: str,
        user_name: str,
        company_name:str,
        company_group: str,
        department: str,
        position: str,
        hire_date: str,
        total_tokens: int
):
    result = await collection_object.insert_one({
        "SessionType": session_type,
        "User": {"UserID": user_id,
                 "UserName": user_name,
                 "CompanyName": company_name,
                 "CompanyGroup": company_group,
                 "Department": department,
                 "Position": position,
                 "HireDate": hire_date},
        "ChatHistory": [{"role": "user", "content": old_text}, {"role": "system", "content": new_text}],
        "SessionStartDate": datetime.datetime.utcnow(),
        "FeedbackRate": None,
        "FeedbackComment": None,
        "TotalTokens": total_tokens
    }
    )
    session_id = str(result.inserted_id)
    return session_id


async def update_log_record(
        collection_object,
        session_id: str,
        feedback_rate: int,
        feedback_comment: str
):

    result = collection_object.update_one({"_id": ObjectId(session_id)}, {"$set": {"FeedbackRate": feedback_rate,
                                                                                   "FeedbackComment": feedback_comment}})
    return


async def improve_objective_workflow(
        old_objective_text: str,
        router
):
    system_message = constants.OBJECTIVE_SYSTEM_MESSAGE_PATH
    handler = OpenAIHandler(system_message_path=system_message,
                            few_shot_examples_path=None,
                            initial=True)

    response = await handler.llm_call(old_objective_text, router)
    response = json.loads(response.model_dump_json())

    return response


async def improve_key_result_workflow(
        old_kr_text: str,
        KrZaman: bool,
        KrOlculebilirlik: bool,
        router
):
    system_message = constants.KR_SYSTEM_MESSAGE_PATH.format(zaman_flag= KrZaman, measure_flag= KrOlculebilirlik)
    handler = OpenAIHandler(system_message_path=system_message,
                            few_shot_examples_path=None,
                            initial=True)

    response = await handler.llm_call(old_kr_text, router)
    response = json.loads(response.model_dump_json())

    return response


async def update_base_messages_workflow(
        session_id: str,
        user_id: str,
        user_name: str,
        company_name: str,
        company_group: str,
        department: str,
        position: str,
        hire_date: str,
        user_message: str,
        collection_object,
        base_messages: list,
        session_type: str
):

    if session_id == "":
        base_messages.append(
            {"role": "user",
             "content": f"Username: {user_name}, Job Title: {position}, Company Group: {company_group}, Department: {department}"}
        )
        base_messages.append(
            {"role": "user",
             "content": user_message}
        )
        result = await collection_object.insert_one({
            "SessionType": session_type,
            "User": {"UserID": user_id,
                     "UserName": user_name,
                     "CompanyName": company_name,
                     "CompanyGroup": company_group,
                     "Department": department,
                     "Position": position,
                     "HireDate": hire_date},
            "ChatHistory": base_messages,
            "SessionStartDate": datetime.datetime.utcnow(),
            "SessionEndDate": datetime.datetime.utcnow(),
            "FeedbackRate": None,
            "FeedbackComment": None,
            "TotalTokens": None
        }
        )
        session_id = str(result.inserted_id)

    else:
        find_result = await collection_object.find_one({"_id": ObjectId(session_id)})
        base_messages = find_result["ChatHistory"]

        base_messages.append(
                {"role": "user",
                 "content": user_message}
        )

    return session_id, base_messages


async def end_chat_session(
        collection_object,
        session_id: str,
        feedback_rate: int,
        feedback_comment: str
):

    result = collection_object.update_one({"_id": ObjectId(session_id)}, {"$set": {"FeedbackRate": feedback_rate,
                                                                                   "FeedbackComment": feedback_comment,
                                                                                   "SessionEndDate": datetime.datetime.utcnow()}})
    return result


async def update_chat_history(
        session_id: str,
        base_messages: list,
        collection_object,
        response: dict
):
    total_tokens = response['usage']["total_tokens"]
    new_message = response['choices'][0]['message']['content']

    if new_message != "":
        base_messages.append(
            {
                "role": "system",
                "content": new_message
            }
        )

    result = collection_object.update_one({"_id": ObjectId(session_id)}, {"$set": {"ChatHistory": base_messages,
                                                                                   "SessionEndDate": datetime.datetime.utcnow(),
                                                                                   "TotalTokens": total_tokens}})

    return session_id


async def chatbot_workflow(
        collection_object,
        session_type: str,
        session_id: str,
        user_id: str,
        user_name: str,
        company_name: str,
        company_group: str,
        department: str,
        position: str,
        hire_date: str,
        user_message: str,
        feedback_rate: int,
        feedback_comment: str,
        router

):

    if feedback_rate != 0:
        asyncio.create_task(end_chat_session(
            collection_object=collection_object,
            session_id=session_id,
            feedback_rate=feedback_rate,
            feedback_comment=feedback_comment
        ))
        response = {"SessionID": session_id,
                    "UserID": user_id,
                    "Response": "Feedback için teşekkürler!"}

        return response
    try:
        prompt_user_name = user_name.split()[0].capitalize()
    except:
        prompt_user_name = "Anonymous"
    to_eng_char = str.maketrans("çğıöşüİÇĞÖŞÜ", "cgiosuICGOSU")
    prompt_position = position.translate(to_eng_char)

    if session_id == "":
        if session_type == "OKRSuggestion":
            system_message = constants.OKR_KR_SUGGESTION_CHATBOT_SYSTEM_MESSAGE_PATH.format(
                user_message=user_message
            )

        elif session_type == "DevelopmentKRSuggestion":
            system_message = constants.DEVELOPMENT_KR_SUGGESTION_CHATBOT_SYSTEM_MESSAGE_PATH.format(
                username=prompt_user_name,
                user_message=user_message,
                job_title=prompt_position,
                department=department,
                industry=company_group
            )

        elif session_type == "AlignedOKRSuggestion":
            system_message = constants.ALIGNED_OKR_SUGGESTION_CHATBOT_SYSTEM_MESSAGE_PATH

        elif session_type == "OKRFreeChat":
            system_message = constants.CHATBOT_SYSTEM_MESSAGE_PATH.format(
                user_message=user_message
            )

        elif session_type == "ImproveObjectiveChat":
            system_message = constants.IMPROVE_OBJECTIVE_SYSTEM_MESSAGE_PATH.format(
                username=prompt_user_name
            )

        else:
            raise Exception("Invalid chat_category!")

        handler = OpenAIHandler(system_message_path=system_message,
                                few_shot_examples_path=None,
                                initial=True)
        base_messages = copy.deepcopy(handler.base_messages)
    else:
        system_message = ""
        handler = OpenAIHandler(system_message_path=system_message,
                                few_shot_examples_path=None,
                                initial=False)
        base_messages = [""]

    user_message = unquote(user_message)
    session_id, base_messages = await update_base_messages_workflow(
        session_id=session_id,
        user_id=user_id,
        user_name=user_name,
        company_name=company_name,
        company_group=company_group,
        department=department,
        position=position,
        hire_date=hire_date,
        user_message=user_message,
        collection_object=collection_object,
        base_messages=base_messages,
        session_type=session_type
    )

    response = await handler.llm_chat(base_messages, router)
    response = json.loads(response.model_dump_json())
    response_message = response['choices'][0]['message']['content']

    asyncio.create_task(update_chat_history(
        session_id=session_id,
        base_messages=base_messages,
        collection_object=collection_object,
        response=response
    ))

    response = {"SessionID": session_id,
                "UserID": user_id,
                "Response": response_message}

    return response
