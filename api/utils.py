import os
import json
import io
import ssl
import re
from azure.storage.blob import BlobServiceClient
import urllib.request

def merge_nested_dicts(dict1, dict2):
    """
    Recursively merges two dictionaries (3 levels deep).

    Args:
        dict1 (dict): First dictionary.
        dict2 (dict): Second dictionary.

    Returns:
        dict: Merged dictionary.
    """
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_nested_dicts(result[key], value)
        else:
            result[key] = value
    return result

def get_span_number(filename):
    """
    Extracts the span number from a filename.

    Args:
        filename (str): The input filename.

    Returns:
        int or None: The span number if found, or None if not found.
    """
    # Use regular expression to extract the span number
    match = re.search(r"(\d+)span", filename)
    if match:
        return int(match.group(1))
    else:
        return None


def allowSelfSignedHttps(allowed):
    # bypass the server certificate verification on client side
    if allowed and not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None):
        ssl._create_default_https_context = ssl._create_unverified_context

def get_aml_predictions(matchups):
    allowSelfSignedHttps(True)
    body = str.encode(json.dumps(matchups))
    url = os.getenv('AML_REST_ENDPOINT')
    api_key = os.getenv('AML_CONNECTION_STRING')
    headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key) }
    req = urllib.request.Request(url, body, headers)
    response = urllib.request.urlopen(req)
    return json.loads(response.read().decode('utf-8'))

def generate_aml_matchups(matchups, blob_storage_manager):
    aml_matchups = []
    for matchup in matchups:
        model = matchup['model']
        isNeutral, isWomens = matchup['isNeutral'], matchup.get('isWomens', False)
        matchup_stats = blob_storage_manager.get_matchup_stats(matchup['team1'], matchup['team2'], get_span_number(model))
        aml_matchups.append({
            'model': model, 
            'team1': matchup_stats['team1']["stats"], 
            'team2': matchup_stats['team2']["stats"], 
            'isWomens': isWomens, 
            'isNeutral': isNeutral
        })
    return aml_matchups

def generate_predictions(matchups, blob_storage_manager):
    aml_matchup_request_body = generate_aml_matchups(matchups, blob_storage_manager)
    aml_predictions = get_aml_predictions(aml_matchup_request_body)
    assert len(aml_predictions) == len(matchups)

    return_body = []
    for i in range(len(matchups)):
        matchup = matchups[i]
        model = matchup['model']
        matchup_stats =blob_storage_manager.get_matchup_stats(matchup['team1'], matchup['team2'], get_span_number(model))
        matchup['team1LastPlayed'], matchup['team2LastPlayed'] = matchup_stats['team1']["lastPlayed"], matchup_stats['team2']["lastPlayed"]
        matchup['predict'], matchup['predictProba'] = aml_predictions[i]['predict'], aml_predictions[i]['predictProba']
        return_body.append(matchup)
    return return_body


class AzureBlobStorageManager:
    def __init__(self, connection_string: str):
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.team_stats = self.download_team_stats()
        self.top25 = self.download_top25()

    def upload_dict_to_blob(self, container_name: str, blob_name: str, data_dict: dict):
        """
        Uploads a Python dictionary as JSON to an Azure Blob Storage container.

        Args:
            container_name (str): Name of the container.
            blob_name (str): Name of the blob.
            data_dict (dict): Python dictionary to upload.

        Returns:
            None
        """
        container_client = self.blob_service_client.get_container_client(container=container_name)
        json_data = json.dumps(data_dict)
        input_stream = io.BytesIO(json_data.encode())
        container_client.upload_blob(name=blob_name, data=input_stream, overwrite=True)

    def download_dict_from_blob(self, container_name: str, blob_name: str) -> dict:
        """
        Downloads a Python dictionary from an Azure Blob Storage container.

        Args:
            container_name (str): Name of the container.
            blob_name (str): Name of the blob.

        Returns:
            dict: Python dictionary retrieved from the blob.
        """
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_data = blob_client.download_blob().readall()
        json_data = blob_data.decode()
        return json.loads(json_data)
    
    def download_team_stats(self):
        return self.download_dict_from_blob('mlmb-api', 'team-stats')
    
    def get_matchup_stats(self, team1: str, team2: str, span: int) -> dict:
        stats = self.team_stats
        team1_stats, team2_stats = stats[f'{span}'][team1], stats[f'{span}'][team2]
        return {'team1': team1_stats, 'team2': team2_stats}
    
    def download_top25(self):
        return self.download_dict_from_blob('mlmb-api', 'top25')
    
    def get_top25(self):
        return self.top25
    
    def reset_blob(self, key: str) -> bool:
        if key != os.getenv('RESET_KEY'):
            return False
        
        self.team_stats = self.download_team_stats()
        self.top25 = self.download_top25()
        return True