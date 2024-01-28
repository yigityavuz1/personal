import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from dotenv import load_dotenv
import uvicorn
import ssl

import src.schemas as _schemas
from src.service import check_bias_workflow, gender_prediction_workflow
from src.service import postprocess

app = FastAPI()
load_dotenv()


# TODO: add "job terminology" to the pipe


@app.on_event("startup")
async def startup_event():
    executor = ThreadPoolExecutor()
    loop = asyncio.get_running_loop()
    loop.set_default_executor(executor)


@app.post("/check_bias/")
async def check_bias_in_job_posting(request_body: _schemas.CheckBiasInput):
    full_text = request_body.ARANILAN_NITELIKLER_BASLIK + '\n' + request_body.ARANILAN_NITELIKLER_METIN + \
                '\n' + request_body.ROL_SORUMLULUK_BASLIK + '\n' + request_body.ROL_SORUMLULUK_METIN
    biased_list = await check_bias_workflow(full_text)

    response_schema = await asyncio.to_thread(postprocess, biased_list, request_body)

    return response_schema


@app.post("/predict_gender/")
async def predict_gender_from_name(request_body: _schemas.GenderPredictInput):
    name = request_body.BASVURAN_AD
    response_schema = _schemas.GenderPredictOutput()
    response_schema.BASVURU_ID = request_body.BASVURU_ID
    response_schema.BASVURAN_AD = request_body.BASVURAN_AD

    prediction_response = await asyncio.to_thread(gender_prediction_workflow, name)
    response_schema.CINSIYET = prediction_response['gender']
    response_schema.ORAN = prediction_response['probability']

    return response_schema


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=5000, ssl_keyfile="./ssl/kockariyerimkey_2024.pem",
                ssl_certfile="./ssl/kockariyerimcert_2024.pem", ssl_keyfile_password="Aa123456.")
