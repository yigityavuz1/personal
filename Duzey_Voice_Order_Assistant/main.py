from fastapi import FastAPI
from data_models import RequestModel
from functions import AgentTest

app = FastAPI()


@app.post("/voice_assistant")
async def voice_assistant(request_body: RequestModel):
    text = request_body.text
    session_id = request_body.sessionID
    cart = request_body.cart

    agent = AgentTest()

    result, cart = agent.run(text, session_id=session_id, cart=cart)
    print(session_id)
    #for i in result['messages']:
    #    print(i)

    return_data = {"cart": cart, "messages": result}
    return return_data