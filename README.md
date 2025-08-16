# VoIP.ms Call Recording Synchronization Script

This project provides a robust Python script to periodically synchronize call recordings from your VoIP.ms account to a local directory. The script is idempotent, resilient to network issues, and designed to be run by a scheduler like `cron`.

## Features

- **Idempotent**: Keeps track of downloaded files and won't download the same recording twice.
- **Resilient**: Implements a retry mechanism with exponential backoff for API requests.
- **Memory-Efficient**: Downloads large files in chunks to minimize memory usage.
- **Configurable**: All credentials and paths are managed via a `config.ini` file.
- **Containerized**: Includes a `Dockerfile` for easy deployment.

## Getting Started

### Prerequisites

- Python 3.7+
- A VoIP.ms account with API access enabled.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/legendary-giggle.git
    cd legendary-giggle
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

Before running the script, you need to configure your credentials and paths.

1.  **Copy the example configuration:**
    The `config.ini` file is where you'll store your settings. A template is provided in the root directory.

2.  **Edit `config.ini`:**
    Open `config.ini` and replace the placeholder values with your actual VoIP.ms credentials and desired paths.

    ```ini
    [voipms]
    username = YOUR_VOIPMS_USERNAME
    password = YOUR_VOIPMS_PASSWORD

    [paths]
    download_dir = ./recordings
    state_file = ./state.json
    ```
    - `username`: Your VoIP.ms API username.
    - `password`: Your VoIP.ms API password.
    - `download_dir`: The local directory where audio files will be saved.
    - `state_file`: The path to the JSON file that tracks downloaded recordings.

## Usage

To run the synchronization script manually, execute the following command in your terminal:

```bash
python sync_recordings.py
```

The script will log its progress to the console. It is recommended to automate the execution of this script using a scheduler.

### Scheduling with Cron (Linux/macOS)

To run the script every hour, you can add the following line to your crontab:

```bash
0 * * * * /usr/bin/python3 /path/to/your/project/sync_recordings.py >> /path/to/your/project/sync.log 2>&1
```

## Docker

You can also run the script in a Docker container for a more isolated environment.

1.  **Build the Docker image:**
    ```bash
    docker build -t voipms-sync .
    ```

2.  **Run the container:**
    Make sure your `config.ini` is correctly filled out. The container will use it to run the script.
    ```bash
    docker run --rm -v "$(pwd)/recordings:/app/recordings" -v "$(pwd)/state.json:/app/state.json" voipms-sync
    ```
    - The `-v` flags mount the local `recordings` directory and `state.json` file into the container. This ensures that your downloaded files and state persist between container runs.
