# HarvestPP Project

This repository contains two Python scripts: `harvestpp.py` and `update_pure.py`, which are used for harvesting and updating profile data for individuals at Utrecht University (UU).

## Overview

- `harvestpp.py`: This script collects data from the UU staff pages and connects it with existing records in the Pure system. It also downloads profile pictures and creates data files needed for subsequent updates.
- `update_pure.py`: This script updates profile information in the Pure system, such as email addresses, profile pictures (if consent is provided), and the 'About' section of the profiles.

## Requirements

To set up this project, you need Python 3 and a few additional packages. The dependencies are listed in `requirements.txt`, which you can generate with the following command:

```sh
pip freeze > requirements.txt
```

To install the dependencies, use:

```sh
pip install -r requirements.txt
```

## Configuration

This project relies on a configuration file named `config.ini`, which contains API keys and URLs required for accessing the Pure and UU APIs. The `config.ini` file should include sections like:

```ini
[Pure]
pure_api_key_crud = YOUR_API_KEY_CRUD
pure_api_key_old = YOUR_API_KEY_OLD
api_url_persons_old = YOUR_API_URL_PERSONS_OLD
api_url_persons_search = YOUR_API_URL_PERSONS_SEARCH
uri_profile_en = YOUR_PROFILE_URI
api_url_base = YOUR_API_URL_BASE

[PP]
api = YOUR_API_URL_PP
filestaff = YOUR_FILENAME
```

Make sure to fill in the appropriate API keys and URLs.

## Running the Scripts

### Step 1: Harvest Data

Run `harvestpp.py` to harvest staff data from the UU staff pages and save it to a JSON file. This script performs the following tasks:

1. Harvests profile data from UU staff pages.
2. Writes harvested data to a file.
3. Connects harvested data with existing records in the Pure system.
4. Downloads profile pictures of staff members.

```sh
python harvestpp.py
```

### Step 2: Update Profiles

After harvesting the data, run `update_pure.py` to update the profiles in the Pure system. This script updates:

1. Email addresses.
2. Profile pictures (if consent is given).
3. The 'About' information.

You can choose to update all profiles or a specific profile based on a `solisid`.

```sh
python update_pure.py
```

## Script Summaries

### `harvestpp.py`
- **Main Functions**:
  - `harvest_json_uustaffpages()`: Harvests staff data from UU staff pages.
  - `harvest_json_and_write_to_file_uustaffpages()`: Writes harvested data to a JSON file.
  - `connect_pure_with_uustaffpages()`: Connects Pure system SolisIDs with corresponding UU staff pages.
  - `dowload_profilepictures()`: Downloads profile pictures for staff members.
  - `fetch_person_data()`: Fetches detailed staff information from the Pure system.
  - `update_profile_information()`: Updates the profile information, including email and photos.

### `update_pure.py`
- **Main Functions**:
  - 'user_choice()': lets user choose between update all or a specific employee
  - `update_persons()`: Updates person records in Pure using harvested data.
  - `main()`: Handles user input to update either all profiles or a specific profile.

## Notes
- Make sure to have proper permissions and valid API keys before running the scripts.
- The whole process of harvesting and updating profiles may take between 2 to 3 hours.

## License
This project is open source. Contact the author for more information.

