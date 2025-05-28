import os
import pickle
from tqdm import tqdm
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# Automatic YouTube Video Uploader
# This script uploads videos from a specified directory to YouTube using the YouTube Data API v3.


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_FILE = "client_secret.json"
CREDENTIALS_PICKLE_FILE = "youtube_token.pickle"
MAX_VIDEOS_PER_DAY = 8

def files_to_upload():
    # find file inside the nested folder "opptak" where the videos are located inside folders for each game, opptake is located in F:\
    base_path = "F:\Captures"
    if not os.path.exists(base_path):
        print(f"Base path {base_path} does not exist.")
        return []
    files = []
    #find x most old files in the base_path
    for root, dirs, filenames in os.walk(base_path):
        for filename in filenames:
            if filename.endswith(('.mp4')):
                full_path = os.path.join(root, filename)
                files.append(full_path)
    files.sort(key=os.path.getmtime, reverse=False) # Sort by modification time, oldest first
    return files[:MAX_VIDEOS_PER_DAY]
    
def get_authenticated_service():
    credentials = None
    if os.path.exists(CREDENTIALS_PICKLE_FILE):
        with open(CREDENTIALS_PICKLE_FILE, 'rb') as token:
            credentials = pickle.load(token)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            credentials = flow.run_local_server(port=0)
        with open(CREDENTIALS_PICKLE_FILE, 'wb') as token:
            pickle.dump(credentials, token)
    return build("youtube", "v3", credentials=credentials)

class TqdmBufferedReader(io.BufferedReader):
    def __init__(self, raw, total):
        super().__init__(raw)
        self._progress_bar = tqdm(total=total, unit='B', unit_scale=True, desc='Uploading')

    def read(self, amt=None):
        chunk = super().read(amt)
        self._progress_bar.update(len(chunk))
        return chunk

    def close(self):
        self._progress_bar.close()
        super().close()

def upload_video(file_path, title="Test Title", description="Test Description"):
    youtube = get_authenticated_service()

    file_size = os.path.getsize(file_path)
    with open(file_path, 'rb') as f:
        buffered = TqdmBufferedReader(f, total=file_size)
        media = MediaIoBaseUpload(buffered, mimetype='video/*', chunksize=-1, resumable=True)

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["gaming", "PC"],
                    "categoryId": "20"  # Category ID for "Gaming"
                },
                "status": {
                    "privacyStatus": "unlisted"  # Change to "public" or "private" as needed
                }
            },
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
        print("✅ Upload complete! Video ID:", response["id"])

if __name__ == "__main__":

    files = files_to_upload()
    uploaded_files = []
    print("Starting YouTube video upload process...")
    if not files:
        print("No files to upload.")
    else:
        print(f"Found {len(files)} files to upload.")
        for file in files:
            try:
                print(f"Uploading {file}...")
                upload_video(file, title=os.path.basename(file), description="Uploaded via YouTube API")
                uploaded_files.append(file)
            except Exception as e:
                print(f"Error uploading {file}: {e}")
        
        # Delete only the files we uploaded
        for file in uploaded_files:
            try:
                os.remove(file)
                print(f"Deleted file: {file}")
            except Exception as e:
                print(f"Error deleting file {file}: {e}")
 
