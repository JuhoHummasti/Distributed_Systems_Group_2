import os

class VideoStorage:
    def __init__(self, storage_dir='videos'):
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def save_video(self, file, video_id):
        file_path = os.path.join(self.storage_dir, video_id)
        file.save(file_path)

    def get_video(self, video_id):
        file_path = os.path.join(self.storage_dir, video_id)
        if os.path.exists(file_path):
            return file_path
        return None