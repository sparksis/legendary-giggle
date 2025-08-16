import configparser
import json
import logging
import os
import time
import requests

# --- Constants ---
# Base URL for the API. Assumed from the prompt.
API_BASE_URL = "https://voip.ms/api/v1"
# Maximum number of retries for network requests.
MAX_RETRIES = 3

def setup_logging():
    """Configure logging to print to standard output."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def fetch_recordings_list(username, password):
    """
    Fetches the list of available call recordings from the API.

    Implements a retry mechanism with exponential backoff for resilience.

    Args:
        username (str): The VoIP.ms API username.
        password (str): The VoIP.ms API password.

    Returns:
        list: A list of recording objects from the API, or None if an
              unrecoverable error occurs.
    """
    url = f"{API_BASE_URL}/recordings"
    params = {'username': username, 'password': password}

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            # Assuming the actual list is nested under a 'recordings' key.
            # If the structure is different, this line needs adjustment.
            data = response.json()
            if "recordings" in data and isinstance(data["recordings"], list):
                logging.info("Successfully fetched the list of recordings from the API.")
                return data["recordings"]
            else:
                logging.error(f"API response format is unexpected. Response: {data}")
                return None

        except requests.exceptions.RequestException as e:
            logging.error(f"Attempt {attempt + 1}/{MAX_RETRIES}: Failed to connect to API: {e}")
            if attempt < MAX_RETRIES - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                logging.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logging.error("All retry attempts failed. Could not fetch recordings list.")
                return None
        except json.JSONDecodeError:
            logging.error("Failed to decode JSON from API response.")
            return None

def download_single_recording(recording_id, username, password, download_path):
    """
    Downloads a single recording file from the API using a streaming approach.

    Args:
        recording_id (str): The unique identifier for the recording.
        username (str): The VoIP.ms API username.
        password (str): The VoIP.ms API password.
        download_path (str): The full local path to save the file.

    Returns:
        bool: True if the download was successful, False otherwise.
    """
    url = f"{API_BASE_URL}/recordings/{recording_id}/file"
    params = {'username': username, 'password': password}

    try:
        logging.info(f"Starting download for recording ID: {recording_id}")
        with requests.get(url, params=params, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(download_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logging.info(f"Successfully downloaded and saved to {download_path}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download recording {recording_id}. Error: {e}")
        return False

def synchronize_recordings(config):
    """
    Orchestrates the synchronization process.

    - Loads local state.
    - Fetches remote recordings list.
    - Identifies and downloads new recordings.
    - Updates local state.
    """
    # --- 1. Load configuration ---
    try:
        username = config['voipms']['username']
        password = config['voipms']['password']
        download_dir = config['paths']['download_dir']
        state_file = config['paths']['state_file']
    except KeyError as e:
        logging.error(f"Configuration error: Missing key {e} in config.ini")
        return

    # --- 2. Create download directory if it doesn't exist ---
    os.makedirs(download_dir, exist_ok=True)

    # --- 3. Load local state ---
    downloaded_ids = set()
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                # Load IDs into a set for efficient lookups
                downloaded_ids = set(json.load(f))
            logging.info(f"Loaded {len(downloaded_ids)} previously downloaded recording IDs from state.")
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Could not read or parse state file at {state_file}. Error: {e}")
            # Depending on desired behavior, you might want to exit here.
            # For resilience, we'll proceed assuming no prior state.
            downloaded_ids = set()
    else:
        logging.info("State file not found. Starting with a clean state.")

    # --- 4. Fetch list of available recordings ---
    remote_recordings = fetch_recordings_list(username, password)
    if remote_recordings is None:
        logging.error("Halting synchronization due to failure in fetching recording list.")
        return

    # --- 5. Identify new recordings ---
    remote_ids = {rec['id'] for rec in remote_recordings if 'id' in rec}
    new_recording_ids = list(remote_ids - downloaded_ids)

    if not new_recording_ids:
        logging.info("No new recordings to download. Synchronization is complete.")
        return

    logging.info(f"Found {len(new_recording_ids)} new recordings to download.")

    # --- 6. Download new recordings ---
    successfully_downloaded_ids = []
    for rec_id in new_recording_ids:
        # Assuming a file extension. This could be made configurable.
        file_path = os.path.join(download_dir, f"{rec_id}.mp3")
        success = download_single_recording(rec_id, username, password, file_path)
        if success:
            successfully_downloaded_ids.append(rec_id)

    # --- 7. Update state file ---
    if successfully_downloaded_ids:
        updated_ids = downloaded_ids.union(set(successfully_downloaded_ids))
        try:
            with open(state_file, 'w') as f:
                # Convert set to list for JSON serialization
                json.dump(list(updated_ids), f, indent=4)
            logging.info(f"Successfully updated state file with {len(successfully_downloaded_ids)} new recordings.")
        except IOError as e:
            logging.error(f"Could not write to state file at {state_file}. Error: {e}")

def main():
    """Main entry point for the script."""
    setup_logging()
    logging.info("Starting call recording synchronization script.")

    config = configparser.ConfigParser()
    try:
        if not config.read('config.ini'):
            logging.error("Error: config.ini not found or is empty.")
            return
    except configparser.Error as e:
        logging.error(f"Error parsing config.ini: {e}")
        return

    synchronize_recordings(config)

    logging.info("Synchronization script finished.")

if __name__ == "__main__":
    main()
