import os
import json
import re
import numpy as np
import joblib


def init():
    global mens_models
    global womens_models

    mens_model_dir, womens_model_dir = os.path.join(os.getenv("AZUREML_MODEL_DIR"), "model/mens/"), os.path.join(os.getenv("AZUREML_MODEL_DIR"), "model/womens/")
    mens_filenames, womens_filenames = [filename for filename in os.listdir(mens_model_dir)], [filename for filename in os.listdir(womens_model_dir)]
    mens_models, womens_models = {filename.split('.pkl')[0]: joblib.load(f'{mens_model_dir}{filename}') for filename in mens_filenames}, {filename.split('.pkl')[0]: joblib.load(f'{womens_model_dir}{filename}') for filename in womens_filenames}


def run(raw_data):
    def get_span_number(filename):
        match = re.search(r"(\d+)span", filename)
        if match:
            return int(match.group(1))
        else:
            return None
        
    def ensemble(input, models, span):
        counter = 0
        predict, predict_proba = 0, [0, 0]
        for key in models:
            if f'{span}span_' in key:
                model = models[key]
                predict += model.predict(input)[0]
                proba = model.predict_proba(input)
                predict_proba[0], predict_proba[1] = predict_proba[0] + proba[0][0], predict_proba[1] + proba[0][1]
                counter += 1
        return {
            'predict': [int(predict / counter)], 
            'predict_proba': [predict_proba[0] / counter, predict_proba[1] / counter]
        }

    results = []
    payload = json.loads(raw_data)
    for matchup in payload:
        input = np.array([matchup['team2'] + matchup['team1'] + [int(matchup['isNeutral'])]])
        models = mens_models if not matchup['isWomens'] else womens_models
        if 'ensemble' in matchup['model']:
            ensemble_result = ensemble(input, models, get_span_number(matchup['model']))
            matchup['predict'], matchup['predictProba'] = ensemble_result['predict'], ensemble_result['predict_proba']
        else:
            model = models[matchup['model']]
            predict, predict_proba = model.predict(input), model.predict_proba(input)
            matchup['predict'], matchup['predictProba'] = predict.tolist(), predict_proba.tolist()[0]
        results.append(matchup)
    return results