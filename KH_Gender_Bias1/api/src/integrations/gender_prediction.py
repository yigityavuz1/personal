import pandas as pd


class GenderPredictionHandler:
    def __init__(self, database_path=None):
        self.df = self.load_data(database_path)

    def load_data(self, database_path):
        with pd.ExcelFile(database_path) as xls:
            df = pd.read_excel(xls)
            df['name'] = df['name'].str.lower()  # Convert names to lowercase for easy comparison
        return df

    def get_gender_probability(self, name):
        data = self.df[self.df['name'] == name]
        if not data.empty:
            max_probability = data.loc[data['gender_prob'].idxmax()]
            return {"gender": max_probability['gender'], "probability": max_probability['gender_prob']}
        else:
            return {"gender": "unknown", "probability": 0.0}

    def predict_gender(self, name):
        data = name.lower().split()  # Convert name to lowercase and split it
        max_probability = {"gender": None, "probability": 0.0}

        for n in data:
            result = self.get_gender_probability(n)
            if result["probability"] > max_probability["probability"]:
                max_probability = result

        return {"name": name, "gender": max_probability["gender"], "probability": max_probability["probability"]}