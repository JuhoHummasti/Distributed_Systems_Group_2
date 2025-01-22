def validate_video_file(file):
    allowed_extensions = {'mp4', 'avi', 'mov'}
    return '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_unique_id():
    import uuid
    return str(uuid.uuid4())