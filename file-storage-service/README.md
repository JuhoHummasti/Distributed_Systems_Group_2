# File Storage Service

This is a file storage service designed to store and manage video files in a core network. It provides an API for uploading and retrieving video files using Flask.

## Project Structure

```
file-storage-service
├── src
│   ├── app.py          # Entry point of the application
│   ├── storage
│   │   └── __init__.py # Contains VideoStorage class for managing video files
│   ├── utils
│   │   └── __init__.py # Utility functions for file handling
├── requirements.txt     # Lists project dependencies
└── README.md            # Documentation for the project
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/file-storage-service.git
   cd file-storage-service
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python src/app.py
   ```

## Usage

- To upload a video file, send a POST request to `/upload` with the video file included in the form data.
- To retrieve a video file, send a GET request to `/video/<video_id>` where `<video_id>` is the unique identifier for the video.

## Test commands

```
curl -X POST -F "file=@/home/matti/Videos/Webcam/2025-01-22-145407.mp4" http://127.0.0.1:8000/upload
```

```
curl -O http://127.0.0.1:8000/video/efdad15f-8849-4062-a2fa-af4edd4c47b9
```

## License

This project is licensed under the MIT License. See the LICENSE file for more details.