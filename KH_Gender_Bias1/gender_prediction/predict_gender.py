from fastapi import FastAPI
import pandas as pd

app = FastAPI()


def load_data():
    df = pd.read_excel('../data/name_gender_database.xlsx', engine='openpyxl')
    df['name'] = df['name'].str.lower()  # Convert names to lowercase for easy comparison
    return df


def get_gender_probability(name, df):
    data = df[df['name'] == name]
    if not data.empty:
        max_probability = data.loc[data['gender_prob'].idxmax()]
        return {"gender": max_probability['gender'], "probability": max_probability['gender_prob']}
    else:
        return {"gender": "unknown", "probability": 0.0}


@app.get("/predict/")
async def predict_gender(name: str):
    df = load_data()
    data = name.lower().split()  # Convert name to lowercase and split it
    max_probability = {"gender": None, "probability": 0.0}

    for n in data:
        result = get_gender_probability(n, df)
        if result["probability"] > max_probability["probability"]:
            max_probability = result

    return {"name": name, "gender": max_probability["gender"], "probability": max_probability["probability"]}


