from src.integrations import GenderPredictionHandler
from src import constants


def gender_prediction_workflow(name: str):
    handler = GenderPredictionHandler(database_path=constants.NAME_DATABASE_PATH)
    gender_prediction_response = handler.predict_gender(name)
    return gender_prediction_response

