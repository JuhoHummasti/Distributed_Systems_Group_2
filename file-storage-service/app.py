from flask import Flask, request, jsonify, send_file
from utils.video_storage import VideoStorage
from utils.validators import validate_video_file, generate_unique_id
import os

app = Flask(__name__)
video_storage = VideoStorage()

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not validate_video_file(file):
        return jsonify({'error': 'Invalid video file format'}), 400

    video_id = generate_unique_id()
    video_storage.save_video(file, video_id)
    return jsonify({'message': 'File uploaded successfully', 'video_id': video_id}), 201

@app.route('/video/<video_id>', methods=['GET'])
def get_video(video_id):
    video = video_storage.get_video(video_id)
    if video is None:
        return jsonify({'error': 'Video not found'}), 404
    return send_file(video, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)