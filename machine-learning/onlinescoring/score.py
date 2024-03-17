import os
import json
import numpy as np
import joblib


def init():
    global mens_models
    global womens_models

    mens_model_dir, womens_model_dir = os.path.join(os.getenv("AZUREML_MODEL_DIR"), "model/mens/"), os.path.join(os.getenv("AZUREML_MODEL_DIR"), "model/womens/")
    mens_filenames, womens_filenames = [filename for filename in os.listdir(mens_model_dir)], [filename for filename in os.listdir(womens_model_dir)]
    mens_models, womens_models = {filename.split('.pkl')[0]: joblib.load(f'{mens_model_dir}{filename}') for filename in mens_filenames}, {filename.split('.pkl')[0]: joblib.load(f'{womens_model_dir}{filename}') for filename in womens_filenames}


def run(raw_data):
    results = []
    payload = json.loads(raw_data)
    for matchup in payload:
        input = np.array([matchup['team2'] + matchup['team1'] + [int(matchup['isNeutral'])]])
        models = mens_models if not matchup['isWomens'] else womens_models
        model = models[matchup['model']]
        predict, predict_proba = model.predict(input), model.predict_proba(input)
        matchup['predict'], matchup['predictProba'] = predict.tolist(), predict_proba.tolist()[0]
        results.append(matchup)
    return results