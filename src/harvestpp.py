import base64
import requests
import os
import pathlib
import configparser

import pandas as pd
from datetime import datetime, time
import numpy as np
import math
import json
import logging


config = configparser.ConfigParser()
config.read('config.ini')
API_KEY_CRUD = config['Pure']['pure_api_key_crud']
API_KEY_OLD = config['Pure']['pure_api_key_old']
API_PP = config['PP']['api']
URL_PERSONS_OLD = config['Pure']['api_url_persons_old']
URL_PERSONS_NEW_SEARCH = config['Pure']['api_url_persons_search']
URI_PROFILE = config['Pure']['uri_profile_en']
API_NEW_BASE = config['Pure']['api_url_base']

headers = {
    "accept": "application/json",
    "api-key": API_KEY_CRUD,
    "content-type": "application/json"
}
UUSTAFF_MAX_FACULTY_NR = 25
UUSTAFF_HARVEST_FILENAME = config['PP']['filestaff']
UUSTAFF_MAX_RECS_TO_HARVEST = 1000               # 0 = all records
# We can harvest many fields from the UU staff pages. For now,
# we only need a few.
UUSTAFF_FIELDS_TO_HARVEST = [
                             # 'ContactDetails',
                             'Email',
                             'Bio',
                             # # 'Faculties',        # Here 'Positions' is used.
                             # 'FocusAreas',
                             # 'Id',
                             # # 'Images',
                             # # 'KeyPublications',
                             # # 'LastUpdate',
                             # # 'Links',
                             # 'LinksSocialMedia',
                             # # 'Name',
                             # 'NameShort',
                             # 'Organisation',
                             'PhotoUrl',
                             # 'Positions',
                             # # 'Prizes',
                             # # 'Profile',
                             # # 'Projects',
                             # # 'ProjectsCompleted',
                             # # 'Publications',
                             # 'Skills'
                             ]



UU_WEBSITE = 'https://www.uu.nl'
UUSTAFF_FACULTY_ENDPOINT = '/Public/GetEmployeesOrganogram?f='
UUSTAFF_EMPLOYEE_ENDPOINT = '/Public/getEmployeeData?page='
UUSTAFF_SOLISID_ENDPOINT = '/RestApi/getmedewerkers?selectie=solisid:'
UUSTAFF_PHOTO_ENDPOINT = '/Public/GetImage?Employee='
# Define the file path relative to the script's location
project_root = os.path.dirname(os.path.dirname(__file__))  # Go up one level from src/
files_dir = os.path.join(project_root, 'files')

def timestamp(seconds: bool = False) -> str:
    """Get a timestamp only consisting of a time.

    :param seconds: If True, also show seconds in the timestamp.
    :return: the timestamp.
    """
    now = datetime.now()
    if seconds:
        time_stamp = now.strftime("%H:%M:%S")
    else:
        time_stamp = now.strftime("%H:%M")
    return time_stamp

def harvest_json_uustaffpages(url: str, max_recs_to_harvest: int = 0) -> list:
    """
    :param url: The base URL for harvesting data from the UU staff pages.
    :param max_recs_to_harvest: The maximum number of records to harvest. If set to 0, all available records will be harvested.
    :return: A list of dictionaries containing the harvested employee data.
    """
    print('Harvesting json data from ' + url + '.')

    all_records = 9999999999                # a large number
    if max_recs_to_harvest == 0:
        max_recs_to_harvest = all_records
    json_data = []
    count = 0
    for faculty_nr in range(UUSTAFF_MAX_FACULTY_NR):
        if count >= max_recs_to_harvest:
            break
        print('[faculty nr ' + str(faculty_nr) + ' at ' + timestamp() + ']')
        # 'l-EN' ensures that phone numbers are preceded with "+31".
        # 'fullresult=true' or '=false' only differ in 'Guid' field value.
        faculty_url = url + UUSTAFF_FACULTY_ENDPOINT + str(faculty_nr) + '&l=EN&fullresult=true'
        print (faculty_url)
        faculty_response = requests.get(faculty_url)
        if faculty_response.status_code != requests.codes.ok:
            print('harvest_json_uustaffpages(): error during harvest faculties.')
            print('Status code: ' + str(faculty_response.status_code))
            print('Url: ' + faculty_response.url)
            print('Error: ' + faculty_response.text)
            exit(1)
        faculty_page = faculty_response.json()
        if 'Employees' not in faculty_page:
            # Empty faculty.
            continue
        if len(faculty_page['Employees']) == 0:
            # Empty faculty.
            continue

        df_employees = pd.DataFrame(faculty_page['Employees'])
        df_employees_url = df_employees['Url']
        df_employees_url.dropna(axis=0, how='any', inplace=True)
        if df_employees_url is None:
            # Nothing found.
            continue

        employees_of_faculty = list(df_employees_url)
        for employee_id in employees_of_faculty:
            if count >= max_recs_to_harvest:
                break
            employee_url = url + UUSTAFF_EMPLOYEE_ENDPOINT + employee_id + '&l=EN'

            employee_response = requests.get(employee_url)
            if employee_response.status_code != requests.codes.ok:
                print('harvest_json_uustaffpages(): error during harvest employees.')
                print('Status code: ' + str(employee_response.status_code))
                print('Url: ' + employee_response.url)
                print('Error: ' + employee_response.text)
                exit(1)
            employee_page = employee_response.json()

            if 'Employee' in employee_page:
                parse = {}
                # print(employee_page)
                parse['Employee_Id'] = employee_id
                for element in UUSTAFF_FIELDS_TO_HARVEST:

                    if element in employee_page['Employee']:
                        tmp = employee_page['Employee'][element]
                        if isinstance(tmp, list) and len(tmp) == 0:
                            continue
                        if tmp is not None:
                            parse[element] = tmp

                json_data.append(parse)

            count += 1
            if count % 50 == 0:
                print(count, '(' + timestamp() + ')  ', end='', flush=True)
            if count % 500 == 0:
                print('\n', end='', flush=True)

    print('Done at ' + timestamp() + '.\n')

    return json_data

def datetimestamp(seconds: bool = False) -> str:
    """Get a timestamp consisting of a date and a time.

    :param seconds: If True, also show seconds in the timestamp.
    :return: the timestamp.
    """
    now = datetime.now()
    if seconds:
        datetime_stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    else:
        datetime_stamp = now.strftime("%Y-%m-%d %H:%M")
    return datetime_stamp



def harvest_json_and_write_to_file_uustaffpages(filename: str,
                                                url: str,
                                                max_recs_to_harvest: int = 0) -> list:
    """
    :param filename: Path to the file where the JSON data will be written.
    :param url: URL from which the JSON data is harvested.
    :param max_recs_to_harvest: Maximum number of records to harvest from the URL. Defaults to 0, which means no limit.
    :return: List of JSON objects harvested from the URL.
    """
    print('STEP 1: Harvest profile page information')
    json_data = harvest_json_uustaffpages(url=url,
                                          max_recs_to_harvest=max_recs_to_harvest)

    if len(json_data) == 0:
        return []


    # Ensure the 'files' directory exists
    os.makedirs(files_dir, exist_ok=True)
    json_path = os.path.join(files_dir, filename)
    # Save JSON
    with open(json_path, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)
    return json_data


def connect_pure_with_uustaffpages(url, solislist):
    """
    :param url: The base URL for the UU staff pages API endpoint.
    :param solislist: A list of dictionaries, where each dictionary contains `employee_id` and `uuid` of individuals.
    :return: A pandas DataFrame containing the parsed and consolidated data of SolisIDs and corresponding UU staff pages information.
    """
    print('STEP 3: Connect Pure SolisIDs with corresponding persons from UU staff pages from ' + url + UUSTAFF_SOLISID_ENDPOINT
         + ' in batches of 50...')
    parse_result = pd.DataFrame()
    parse_chunk = []  # List of dictionaries for parsed results
    batch_size = 50  # Number of SolisIDs to process in a single request

    # Group the SolisIDs into batches of `batch_size`
    solis_batches = [solislist[i:i + batch_size] for i in range(0, len(solislist), batch_size)]

    for batch_index, batch in enumerate(solis_batches, start=1):

        solis_ids = ",".join(solis['employee_id'] for solis in batch)
        solis_url = f"{url}{UUSTAFF_SOLISID_ENDPOINT}{solis_ids}"


        response = requests.get(solis_url)
        if response.status_code != requests.codes.ok:
            print('connect_pure_with_uustaffpages(): error during batch request.')
            print('Status code: ' + str(response.status_code))
            print('Url: ' + response.url)
            print('Error: ' + response.text)
            exit(1)

        pages = response.json()
        if not pages:
            continue

        for page in pages:
            solis_id = (page.get('SolisID') or '').upper()
            if not solis_id:
                continue

            uustaff_page_url = page.get('UrlEN') or page.get('UrlNL', '')
            if not uustaff_page_url:
                continue

            path = pathlib.PurePath(uustaff_page_url)
            solis_uuid = next((solis['uuid'] for solis in batch if solis['employee_id'] == solis_id), None)

            parse_line = {
                'SOLIS_ID': str(solis_id),
                'UUID': str(solis_uuid) if solis_uuid else '',
                'Email': str(page.get('Email', '')),
                'DescriptionEN': str(page.get('DescriptionEN', '')),
                'DescriptionNL': str(page.get('DescriptionNL', '')),
                'UrlProfielfoto': str(page.get('UrlProfielfoto', '')),
                'UrlEN': str(page.get('UrlEN', '')),
                'ToestemmingProfielfotoInExterneApps': str(page.get('ToestemmingProfielfotoInExterneApps', '')),
                'UUSTAFF_PAGE_ID': str(path.name)
            }

            parse_chunk.append(parse_line)

        # print(f'Batch {batch_index} processed at ' + timestamp())
        count  = batch_index * 50
        print(count, '(' + timestamp() + ')  ', end='', flush=True)
        if count % 500 == 0:
            print('\n', end='', flush=True)


    print('\n', end='', flush=True)

    parse_chunk_df = pd.DataFrame(parse_chunk)
    parse_result = pd.concat([parse_result, parse_chunk_df], ignore_index=True)
    parse_result.dropna(axis=0, how='all', inplace=True)
    parse_result.drop_duplicates(keep='first', inplace=True, ignore_index=True)
    print('Done at ' + timestamp() + '.\n')
    return parse_result


def persons_active():
    """
       Fetches and returns a list of active persons from the research portal API.
       The function iteratively requests paginated data from the API and extracts
       the 'uuid' and 'employee_id' for each person if both are available.

       :return: A list of dictionaries, each containing 'uuid' and 'employee_id'.
       """

    print('STEP 2: Harvest active persons in Pure')
    print(f'Harvesting active persons from {URL_PERSONS_OLD}')
    count = 0
    page_size = 20
    page = 1
    all_data = []
    # Add headers with 'Accept: application/json'
    headers = {
        'Accept': 'application/json'
    }
    while True:
        # Prepare the request URL with the current page

        request_url = f"{URL_PERSONS_OLD}?pageSize={page_size}&page={page}&apiKey={API_KEY_OLD}"

        # Make the GET request
        response = requests.get(request_url, headers=headers)
        response.raise_for_status()  # Will raise an error if the request fails

        # Parse the JSON response
        data = response.json()
        # Extract the items from the response
        items = data.get('items', [])
        # Check if there are any items
        if not items:
            break

        for person in items:
            uuid = person.get('uuid')
            employee_id = None
            count += 1
            if count % 50 == 0:
                print(count, '(' + timestamp() + ')  ', end='', flush=True)
            if count % 500 == 0:
                print('\n', end='', flush=True)
            # Search for employee ID in the 'ids' list
            ids_list = person.get('ids', [])
            for identifier in ids_list:
                # Check if the ID type is 'Employee ID'
                id_type = identifier.get('type', {}).get('term', {}).get('text', [])
                if any(entry.get('value') == 'Employee ID' for entry in id_type):
                    employee_id = identifier.get('value', {}).get('value')
                    break

            # Append the UUID and Employee ID if both are found
            if uuid and employee_id:
                all_data.append({'uuid': uuid, 'employee_id': employee_id})

        page += 1


        # for testing
        # if page >20:
        #     break


    df_path = os.path.join(files_dir, 'active_persons.csv')
    # Convert list of dictionaries to a DataFrame
    df = pd.DataFrame(all_data)

    # Save DataFrame to CSV
    df.to_csv(df_path, index=False)
    print('end fetching active persons from pure')
    return all_data


def dowload_profilepictures(parsed_results):


    # Define the file path relative to the script's location
    print('STEP 4: start downloading profile pictures from PP')
    project_root = os.path.dirname(os.path.dirname(__file__))  # Go up one level from src/
    files_dir = os.path.join(project_root, 'files')
    # json_path = os.path.join(files_dir, 'filesuustaff_harvest.json')
    # # Load JSON data from file
    # try:
    #     with open(json_path, 'r') as json_file:
    #         uustaff = json.load(json_file)
    #     # print(f"Data read from JSON: {uustaff}")
    # except FileNotFoundError:
    #     print(f"File not found: {json_path}")
    # except json.JSONDecodeError as e:
    #     print(f"Error decoding JSON: {e}")
    # file_path = "uustaff_harvest.json"
    #
    # # Convert JSON data to a DataFrame
    # json_df = pd.DataFrame(uustaff)
    #
    # # Rename the 'Employee_Id' column in json_df to match the 'UUSTAFF_PAGE_ID' column in the existing DataFrame
    # json_df.rename(columns={'Employee_Id': 'UUSTAFF_PAGE_ID'}, inplace=True)
    #
    # # Merge the two DataFrames on 'UUSTAFF_PAGE_ID'
    #
    # merged_df = parsed_results.merge(json_df, on='UUSTAFF_PAGE_ID', how='left')
    # # Define the path where the merged DataFrame should be saved
    output_path = os.path.join(files_dir, 'uustaff_results.csv')

    # Save the merged DataFrame as a CSV file
    parsed_results.to_csv(output_path, index=False)

    # Merge the two DataFrames on 'UUSTAFF_PAGE_ID'
    # df = parsed_results.merge(json_df, on='UUSTAFF_PAGE_ID', how='left')
    project_root = os.path.dirname(os.path.dirname(__file__))  # Go up one level from src/
    photos_dir = os.path.join(project_root, 'photos')
    # Ensure the 'photos' directory exists
    os.makedirs(photos_dir, exist_ok=True)
    photodf = parsed_results[parsed_results['ToestemmingProfielfotoInExterneApps'] != 'False']
    count = 0
    for index, row in photodf.iterrows():
        url = row['UrlProfielfoto']
        count += 1
        if count % 50 == 0:
            print(count, '(' + timestamp() + ')  ', end='', flush=True)
        if count % 500 == 0:
            print('\n', end='', flush=True)

        if url:  # Check if the URL is not None or empty
            # Send a GET request to the URL
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

            # Check if the request was successful
            if response.status_code == 200:
                # Construct the full path for the image file
                filename = os.path.join(photos_dir, f"{row['UUSTAFF_PAGE_ID']}.jpg")

                # Save the image content to a file
                with open(filename, "wb") as file:
                    file.write(response.content)
                # print(f"Image downloaded successfully: {filename}")
            else:
                print(f"Failed to download image for {row['UUSTAFF_PAGE_ID']}. Status code: {response.status_code}")
        # else:
        #     # print(f"No URL found for {row['UUSTAFF_PAGE_ID']}")
    print('End downloading profile pictures from PP')
    return parsed_results


def fetch_person_data(merged_df):
    """
       :param merged_df: Pandas DataFrame containing a column of UUIDs.
       :param api_key: String representing the API key for authorization.
       :return: Dictionary containing combined results from all API requests.
       """
    print('STEP 5: harvesting the personjsons from pure via the crud api')

    # Function to create chunks of a list
    def chunks(lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]


    # Extract UUIDs from the DataFrame
    uuids = merged_df['UUID'].tolist()

    # Split the UUIDs into chunks of 50
    uuid_chunks = list(chunks(uuids, 50))

    # List to store all the results
    all_results = []
    all_items = []
    count = 0
    # Loop through each chunk and make the POST request
    for chunk in uuid_chunks:
        count += 1
        if count % 50 == 0:
            print(count, '(' + timestamp() + ')  ', end='', flush=True)
        if count % 500 == 0:
            print('\n', end='', flush=True)
        # Prepare the payload
        payload = {
            "uuids": chunk,
            "size": 100,
            "offset": 0
        }

        # Make the POST request
        try:

            response = requests.post(URL_PERSONS_NEW_SEARCH, headers=headers, json=payload)
            response.raise_for_status()  # Raise an error if the request fails
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
            continue
            # Extract the items from the JSON response
        response_json = response.json()

        items = response_json.get("items", [])
        all_items.extend(items)

    # Combine all results into a single dictionary
    combined_results = {
        "results": all_items
    }
    return combined_results

def modify_profile_photo(data, name):
    """
    :param data: A dictionary containing profile information where the new photo data will be added.
    :param name: A string used for naming the profile photo. Takes only the first character of the string to generate the photo's file name.
    :return: None. Modifies the input data dictionary in place by adding a new profile photo if the corresponding image file exists.
    """
    # name = name[0]
    # Define project root and photos directory
    project_root = os.path.dirname(os.path.dirname(__file__))  # Go up one level from src/
    photos_dir = os.path.join(project_root, 'photos')

    image_path = os.path.join(photos_dir, f"{name}.jpg")

    if os.path.exists(image_path):
        with open(image_path, 'rb') as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            # Prepare the payload
            new_profile_photo = {
                "fileName": "profilepicture.jpg",
                "mimeType": "image/jpeg",
                "size": 102400,  # Size in bytes (should be <= 1MB)
                "fileData": encoded_image,
                "copyrightConfirmation": True,
                "type": {
                    "uri": "/dk/atira/pure/person/personfiles/portrait",
                    "term": {
                        "en_GB": "Portrait"
                    }
                },
                "caption": {
                    "en": "Profile photo"
                },
                "altText": {
                    "en": "A profile picture"
                },
                "copyrightStatement": {
                    "en": "© 2024 by User"
                }
            }
            if 'profilePhotos' not in data:
                data['profilePhotos'] = []
            # Add the new profile photo to the profilePhotos list
                data['profilePhotos'].append(new_profile_photo)
    else:
        print(f"Warning: The file {image_path} does not exist.")

    return


def modify_email(data, ref_date, email):
    """
       :param data: The dictionary containing staff organization associations and other relevant information.
       :param ref_date: The reference date used to determine valid association periods, as a datetime object.
       :param email: The email address to add to the staff organization association if none exist.
       :return: The existing email if found, or the new email if added.
       """

    if "staffOrganizationAssociations" in data:

        # Check for existing email in valid associations
        for association in data["staffOrganizationAssociations"]:
            # Check if 'period' is present

            if "period" in association:
                assoc_start_date = association["period"].get("startDate")
                assoc_end_date = association["period"].get("endDate")

                # Convert start and end dates to datetime objects if they exist
                assoc_start_datetime = datetime.strptime(assoc_start_date, "%Y-%m-%d") if assoc_start_date else None
                assoc_end_datetime = datetime.strptime(assoc_end_date, "%Y-%m-%d") if assoc_end_date else None

                # Check if the reference date is within the association period
                if assoc_start_datetime and assoc_start_datetime <= ref_date and (
                        not assoc_end_datetime or ref_date <= assoc_end_datetime):
                    # Check if there are existing emails

                    if "emails" in association:
                        for email in association["emails"]:
                            return email.get("value")

                        # If no email is found, add one to this valid association
                    else:

                        new_email_entry = {
                            # "pureId": "new_pure_id",  # Example placeholder
                            "value": email,
                            "type": {
                                "uri": "/dk/atira/pure/person/personemailtype/email",
                                "term": {
                                    "en_GB": "Email"
                                }
                            }
                        }
                        if "emails" not in association:
                            association["emails"] = []
                        association["emails"].append(new_email_entry)
                        return email

            # If no valid association is found
        logging.info("No valid staff organization association found with a valid period for the reference date.")
        return None
    else:
        # If no staffOrganizationAssociations exist at all
        logging.info("No staff organization associations found.")
        return None


def update_profile_information(merged_df, response_json):
    """
       :param merged_df: A DataFrame containing user profiles with their UUID, Bio, Email, and other profile details.
       :param response_json: A JSON object containing a list of profile information to be updated.
       :return: A modified JSON object with updated user profile information.
       """
    today_date = datetime.now().date()
    today_date = datetime.combine(today_date, time())
    print('STEP 6: making the new jsonfile for all persons with new info')


    for result in response_json['results']:
        uuid = result['uuid']

        # Perform a single row lookup for UUID
        row = merged_df.loc[merged_df['UUID'] == uuid]

        if row.empty:
            # UUID not found in merged_df, skip
            continue

        # Extract Bio
        bio_value = row['DescriptionEN'].values[0] if pd.notna(row['DescriptionEN'].values[0]) else \
        row['DescriptionNL'].values[0] if pd.notna(row['DescriptionNL'].values[0]) else None

        # Extract and format URL
        raw_url = row['UrlEN'].values[0] if pd.notna(row['UrlEN'].values[0]) else None
        url_value = f'<p><a href="{raw_url}">{raw_url}</a></p>' if raw_url else None

        if bio_value or url_value:
            profile_info = result.get('profileInformation', [])

            # Update or add 'About' field
            if bio_value:
                about_found = False
                for info in profile_info:
                    if info['type']['term']['en_GB'] == 'About':
                        info['value']['en_GB'] = bio_value
                        about_found = True
                        break

                if not about_found:
                    new_about = {
                        'value': {'en_GB': bio_value},
                        'type': {
                            'uri': URI_PROFILE,
                            'term': {'en_GB': 'About'}
                        }
                    }
                    profile_info.append(new_about)

            # Update or add 'Link to Utrecht University staff page' field
            if url_value:
                url_found = False
                for info in profile_info:
                    if info['type']['term']['en_GB'] == 'Link to Utrecht University staff page':
                        info['value']['en_GB'] = url_value
                        url_found = True
                        break

                if not url_found:
                    new_url = {
                        'value': {'en_GB': url_value},
                        'type': {
                            'uri': "/dk/atira/pure/person/customfields/profiel_url",
                            'term': {'en_GB': 'Link to Utrecht University staff page'}
                        }
                    }
                    profile_info.append(new_url)

            # Update the profile information in the result
            result['profileInformation'] = profile_info


        # Extract Email
        email_value = row['Email'].values[0] if pd.notna(row['Email'].values[0]) else None
        if email_value:
            modify_email(result, today_date, email_value)
        else:
            print(f"Warning: No email found for UUID: {uuid}")

        # Extract UUSTAFF_PAGE_ID for modifying the profile photo
        print()
        name = row['UUSTAFF_PAGE_ID'].values[0] if pd.notna(row['UUSTAFF_PAGE_ID'].values[0]) else None
        if name:
            toestemmingfoto = row['ToestemmingProfielfotoInExterneApps'].values[0] if pd.notna(row['ToestemmingProfielfotoInExterneApps'].values[0]) else None

            if toestemmingfoto == True:
                modify_profile_photo(result, name)
        # Ensure the 'files' directory exists
        os.makedirs(files_dir, exist_ok=True)
        json_path = os.path.join(files_dir, 'input_for_pure2.json')
        # Save JSON
        with open(json_path, 'w') as json_file:
            json.dump(response_json, json_file, indent=4)

    return response_json


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
    count = 0
    for data in updated_response_json['results']:
        data = convert_ndarrays(data)
        count +=1
        api_url = API_NEW_BASE + 'persons/' + data['uuid']
        response = requests.put(api_url, headers=headers, json=data)
    print(f'updated {count} persons')

def print_summary():
    summary = """
    This script will:
    1. Harvest staff data from UU staff pages.
    2. Write harvested data to a file.
    3. Connect the harvested data with existing records in the Pure system.
    4. Download profile pictures of staff members.

    
    The whole proces might take an hour
    Do you wish to proceed? (y/n): 
    """
    print(summary)

def get_user_confirmation():
    while True:
        user_input = input().strip().lower()
        if user_input == 'y':
            print("Proceeding with the script...\n")
            return True
        elif user_input == 'n':
            print("Stopping the script as requested.\n")
            exit(0)
        else:
            print("Invalid input. Please enter 'y' to proceed or 'n' to stop:")


def main():
    print_summary()
    get_user_confirmation()
    # harvest_json_and_write_to_file_uustaffpages(UUSTAFF_HARVEST_FILENAME, API_PP, UUSTAFF_MAX_RECS_TO_HARVEST)
    solislist = persons_active()
    parsed_results = connect_pure_with_uustaffpages(API_PP, solislist)
    merged_df = dowload_profilepictures(parsed_results)
    print('Start update_pure.py to update persons in pure')



if __name__ == '__main__':
    main()