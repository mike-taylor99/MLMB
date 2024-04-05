import os
from dotenv import load_dotenv
from utils import AzureBlobStorageManager, generate_predictions
from flask import Flask, request
from flask_cors import CORS

load_dotenv()

connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
blob_storage_manager = AzureBlobStorageManager(connect_str)

app = Flask(__name__)
CORS(app)

@app.route('/predict', methods=['POST'])
def predict():
   matchups = request.get_json()
   return generate_predictions(matchups, blob_storage_manager)

@app.route('/top25')
def get_top25():
   return blob_storage_manager.get_top25()

@app.route('/top-25/men')
def get_mens_top_25():
   return blob_storage_manager.get_top25(isWomens = False)

@app.route('/top-25/women')
def get_womens_top_25():
   return blob_storage_manager.get_top25(isWomens = True)

@app.route('/reset_blob', methods=['POST'])
def reset_blob():
   reset_key = request.get_json()['key']
   return f'{blob_storage_manager.reset_blob(reset_key)}'

if __name__ == '__main__':
   app.run()