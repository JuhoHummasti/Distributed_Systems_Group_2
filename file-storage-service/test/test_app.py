import unittest
from unittest.mock import patch, MagicMock
from app import app, video_storage

class FileStorageServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('src.app.validate_video_file')
    @patch('src.app.generate_unique_id')
    @patch('src.app.video_storage.save_video')
    def test_upload_video_success(self, mock_save_video, mock_generate_unique_id, mock_validate_video_file):
        mock_validate_video_file.return_value = True
        mock_generate_unique_id.return_value = 'unique_id'
        
        data = {
            'file': (MagicMock(filename='test.mp4'), 'test.mp4')
        }
        response = self.app.post('/upload', data=data, content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('File uploaded successfully', response.get_data(as_text=True))
        self.assertIn('unique_id', response.get_data(as_text=True))

    def test_upload_video_no_file_part(self):
        response = self.app.post('/upload', data={}, content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('No file part', response.get_data(as_text=True))

    def test_upload_video_no_selected_file(self):
        data = {
            'file': (MagicMock(filename=''), '')
        }
        response = self.app.post('/upload', data=data, content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('No selected file', response.get_data(as_text=True))

    @patch('src.app.validate_video_file')
    def test_upload_video_invalid_format(self, mock_validate_video_file):
        mock_validate_video_file.return_value = False
        
        data = {
            'file': (MagicMock(filename='test.txt'), 'test.txt')
        }
        response = self.app.post('/upload', data=data, content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid video file format', response.get_data(as_text=True))

    @patch('src.app.video_storage.get_video')
    def test_get_video_success(self, mock_get_video):
        mock_get_video.return_value = 'http://example.com/video.mp4'
        
        response = self.app.get('/video/unique_id')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('unique_id', response.get_data(as_text=True))
        self.assertIn('http://example.com/video.mp4', response.get_data(as_text=True))

    @patch('src.app.video_storage.get_video')
    def test_get_video_not_found(self, mock_get_video):
        mock_get_video.return_value = None
        
        response = self.app.get('/video/unknown_id')
        
        self.assertEqual(response.status_code, 404)
        self.assertIn('Video not found', response.get_data(as_text=True))

if __name__ == '__main__':
    unittest.main()