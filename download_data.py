import os
import gdown

DATA_PATH = "data"
CREDITS_FILE = f"{DATA_PATH}/credits.csv"
MOVIES_FILE = f"{DATA_PATH}/movies_metadata.csv"

CREDITS_DRIVE_ID = "1Qma0SUoQ56ZthSuaZtw5tORZ0nEOStS-"
MOVIES_DRIVE_ID = "1IJYO07SDczRHZNJ3jRbz3A_VhFRCpzL3"

os.makedirs(DATA_PATH, exist_ok=True)

def download_file(file_id, dest_path):
    """Download a file from Google Drive if not already available."""
    if not os.path.exists(dest_path):
        print(f"Downloading {dest_path} from Google Drive...")
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, dest_path, quiet=False)
    else:
        print(f"{dest_path} already exists. Skipping download.")

# Run downloads only if missing
download_file(CREDITS_DRIVE_ID, CREDITS_FILE)
download_file(MOVIES_DRIVE_ID, MOVIES_FILE)
print("Dataset is ready.")
