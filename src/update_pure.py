import requests
import os
import pathlib
import configparser
import harvestpp as pp
import pandas as pd
from datetime import datetime, time
import numpy as np
import math
import json
import logging
config = configparser.ConfigParser()
config.read('config.ini')

API_KEY_CRUD = config['Pure']['pure_api_key_crud']
API_NEW_BASE = config['Pure']['api_url_base']

# Define the file path relative to the script's location
project_root = os.path.dirname(os.path.dirname(__file__))  # Go up one level from src/
files_dir = os.path.join(project_root, 'files')

def convert_ndarrays(obj):
    """
       :param obj: An object that may contain nested dictionaries, lists, and NumPy arrays.
       :return: An object with the same structure as input but with all NumPy arrays converted to lists.
       """
    if isinstance(obj, dict):
        return {key: convert_ndarrays(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_ndarrays(element) for element in obj]
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj

headers = {
    "accept": "application/json",
    "api-key": API_KEY_CRUD,
    "content-type": "application/json"
}

def update_persons(updated_response_json):
    """
        :param updated_response_json: JSON data that includes potentially nested dictionary or list structures which may contain NaN values and needs updating.
        :return: None. Updates `updated_response_json` in place and sends PUT requests to update person records.
        """

    def find_nan(data, path=""):
        """Recursively find and print where NaN values are in the data."""
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}" if path else key
                find_nan(value, new_path)
        elif isinstance(data, list):
            for index, value in enumerate(data):
                new_path = f"{path}[{index}]"
                find_nan(value, new_path)
        elif isinstance(data, float) and math.isnan(data):
            print(f"NaN value found at: {path}")

    find_nan((updated_response_json))

    updated_response_json = json.loads(updated_response_json)
    for data in updated_response_json['results']:
        data = convert_ndarrays(data)

        api_url = API_NEW_BASE + 'persons/' + data['uuid']
        response = requests.put(api_url, headers=headers, json=data)
        print(response.text)


def read_json():
    # Load JSON data from file
    json_path = os.path.join(files_dir, 'input_for_pure2.json')
    try:
        with open(json_path, 'r') as json_file:
            uustaff = json.load(json_file)
        # print(f"Data read from JSON: {uustaff}")
    except FileNotFoundError:
        print(f"File not found: {json_path}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    file_path = "uustaff_harvest.json"
    return uustaff


def print_summary():
    summary = """
    This script will:
    Update persons in Pure with profile info harvested in harvestpp.py.
    The following information will be updated:
    1. Email address 
    2. Profile picture (if consent is given)
    3. The 'About' information

    You can do this for all persons or a single solisid.
    What would you like to do?

    1. Update all persons
    2. Update a single person (using solisid)
    """
    print(summary)

def get_user_choice():
    while True:
        user_input = input("Enter your choice (1 for all persons, 2 for single solisid): ").strip()
        if user_input == '1':
            print("You have chosen to update all persons.\n")
            return 'all'
        elif user_input == '2':
            solisid = input("Enter the solisid of the person you want to update: ").strip()
            print(f"You have chosen to update the person with solisid: {solisid}\n")
            return solisid
        else:
            print("Invalid input. Please enter '1' for all persons or '2' for a single solisid.")


def confirm_update_all():
    while True:
        user_input = input("Are you sure you want to update all persons in Pure? This action cannot be undone. (y/n): ").strip().lower()
        if user_input == 'y':
            print("Proceeding with updating all persons...\n")
            return True
        elif user_input == 'n':
            print("Aborting the update process.\n")
            exit(0)
        else:
            print("Invalid input. Please enter 'y' to proceed or 'n' to stop:")


def main():
    print_summary()
    user_choice = get_user_choice()
    # Read the CSV file into a DataFrame
    # Define the path to the saved merged DataFrame
    output_path = os.path.join(files_dir, 'merged_uustaff_results.csv')
    try:
        merged_df = pd.read_csv(output_path)
        print("Merged DataFrame successfully loaded.")
    except FileNotFoundError:
        print(f"File not found: {output_path}")
        exit
    except pd.errors.EmptyDataError as e:
        print(f"Error reading CSV file: {e}")
        exit
    if user_choice == 'all':
        if confirm_update_all():
        # Call the function that handles updating all persons

            persons_pure_json = pp.fetch_person_data(merged_df)
            updated_response_json = pp.update_profile_information(merged_df, persons_pure_json)
            pp.update_persons(updated_response_json)
    else:
        # Filter the DataFrame based on 'solisid' column
        merged_df['SOLIS_ID'] = merged_df['SOLIS_ID'].astype(str)
        filtered_df = merged_df[merged_df['SOLIS_ID'] == user_choice]

        if filtered_df.empty:
            print('no person found in csv')
        else:
            persons_pure_json = pp.fetch_person_data(filtered_df)
            updated_response_json = pp.update_profile_information(filtered_df, persons_pure_json)
            pp.update_persons(updated_response_json)

if __name__ == '__main__':
    main()