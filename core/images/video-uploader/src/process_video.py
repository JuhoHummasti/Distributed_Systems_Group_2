import logging
import asyncio
from pathlib import Path
import tempfile
import subprocess
from minio import Minio
import os
from typing import Tuple
from datetime import datetime
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

DATABASE_SERVICE_URL = os.getenv("DATABASE_SERVICE_URL", "http://database-service:8011")

class VideoProcessor:
    def __init__(self):
        self.minio_client = Minio(
            os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv('MINIO_ACCESS_KEY', 'myaccesskey'),
            secret_key=os.getenv('MINIO_SECRET_KEY', 'mysecretkey'),
            secure=False
        )
        self.bucket_name = os.getenv('MINIO_BUCKET', 'videos')
        self.hls_segment_duration = int(os.getenv('HLS_SEGMENT_DURATION', '10'))
        self.processing_tasks = {}  # Track processing tasks
    
    def _generate_thumbnail(self, source_path: str, output_path: str) -> bool:
        """
        Generate a thumbnail from the video using FFmpeg
        Returns: bool indicating success
        """
        try:
            # Ensure the parent directory exists
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)

            # Extract frame at 1 second mark
            cmd = [
                'ffmpeg',
                '-i', source_path,
                '-ss', '1',  # Seek to 1 second
                '-vframes', '1',  # Extract 1 frame
                '-vf', 'scale=480:-1',  # Scale width to 480px, maintain aspect ratio
                '-f', 'image2',  # Output format
                output_path
            ]

            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            if process.returncode != 0:
                logger.error(f"Thumbnail generation failed: {process.stderr}")
                return False

            return True
        except Exception as e:
            logger.error(f"Error generating thumbnail: {str(e)}")
            return False
        
    def _cpu_intensive_processing(self, video_id: str, source_path: str) -> Tuple[bool, str]:
        """
        Process video in a separate process to create HLS chunks
        Returns: Tuple[success: bool, error_message: str]
        """
        try:
            # Log initial file details
            initial_file = Path(source_path)
            logger.info(f"Initial file path: {source_path}")
            logger.info(f"Initial file exists: {initial_file.exists()}")
            logger.info(f"Initial file size: {initial_file.stat().st_size} bytes")

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                hls_dir = temp_dir_path / f"{video_id}_hls"
                hls_dir.mkdir(exist_ok=True)

                # Log temp directory details
                logger.info(f"Temporary directory: {temp_dir}")
                logger.info(f"HLS directory: {hls_dir}")

                # Generate thumbnail
                thumbnail_path = temp_dir_path / f"thumbnails/{video_id}.jpg"
                if not self._generate_thumbnail(source_path, str(thumbnail_path)):
                    return False, "Failed to generate thumbnail"

                # Upload thumbnail to MinIO
                try:
                    self.minio_client.fput_object(
                        self.bucket_name,
                        f"thumbnails/{video_id}.jpg",
                        str(thumbnail_path),
                        content_type="image/jpeg"
                    )
                except Exception as e:
                    logger.error(f"Failed to upload thumbnail: {e}")
                    return False, f"Failed to upload thumbnail: {str(e)}"

                # Detailed FFmpeg command logging
                cmd = [
                    'ffmpeg',
                    '-i', source_path,
                    # '-v', 'debug',  # Increase verbosity
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-profile:v', 'baseline',
                    '-level', '3.0',
                    '-c:a', 'aac',
                    '-ar', '48000',
                    '-b:a', '128k',
                    '-start_number', '0',
                    '-hls_time', str(self.hls_segment_duration),
                    '-hls_list_size', '0',
                    '-f', 'hls',
                    str(hls_dir / 'playlist.m3u8')
                ]


                # Run with detailed process capture
                process = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    cwd=temp_dir
                )

                # Log FFmpeg output
                # logger.info(f"FFmpeg stdout: {process.stdout}")
                # logger.error(f"FFmpeg stderr: {process.stderr}")
                # logger.info(f"FFmpeg return code: {process.returncode}")

                # Check generated files
                generated_files = list(hls_dir.glob('*'))
                logger.info(f"Generated files: {generated_files}")
                for file in generated_files:
                    logger.info(f"File: {file}, Size: {file.stat().st_size} bytes")

                if process.returncode != 0:
                    logger.error(f"FFmpeg error: {process.stderr}")
                    return False, f"FFmpeg failed: {process.stderr}"

                logger.info(f"Uploading HLS files for video {video_id}")
                
                failed_uploads = []
    
                # Upload playlist
                playlist_path = hls_dir / 'playlist.m3u8'
                try:
                    self.minio_client.fput_object(
                        self.bucket_name,
                        f"hls/{video_id}/playlist.m3u8",
                        str(playlist_path),
                        content_type="application/vnd.apple.mpegurl"
                    )
                    # if not self.verify_minio_upload(self.bucket_name, f"hls/{video_id}/playlist.m3u8", playlist_path):
                    #     failed_uploads.append('playlist.m3u8')
                except Exception as e:
                    logger.error(f"Failed to upload playlist: {e}")
                    failed_uploads.append('playlist.m3u8')

                # Upload segments
                for segment in hls_dir.glob("*.ts"):
                    try:
                        remote_path = f"hls/{video_id}/{segment.name}"
                        self.minio_client.fput_object(
                            self.bucket_name,
                            remote_path,
                            str(segment),
                            content_type="video/MP2T"
                        )
                        # if not self.verify_minio_upload(self.bucket_name, remote_path, segment):
                        #     failed_uploads.append(segment.name)
                    except Exception as e:
                        logger.error(f"Failed to upload segment {segment.name}: {e}")
                        failed_uploads.append(segment.name)

                if failed_uploads:
                    raise Exception(f"Failed to upload {len(failed_uploads)} files: {failed_uploads}")

                update_data = {
                    "status": "processed",
                    "time_updated": datetime.utcnow().isoformat()
                }

                client = httpx.AsyncClient()
                response = client.put(
                    f"{DATABASE_SERVICE_URL}/api/v1/items/{video_id}",
                    json=update_data
                )
                if response.status_code != 200:
                    raise HTTPException(status_code=500, detail="Failed to update video status")
                    
                return True, ""

        except Exception as e:
            error_msg = f"Error processing video {video_id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        finally:
            # Close the client if it was opened
            if 'client' in locals():
                client.close()
        
    def verify_minio_upload(self, bucket_name: str, object_name: str, source_path: str) -> bool:
        try:
            # Verify object exists and size matches
            stat = self.minio_client.stat_object(bucket_name, object_name)
            source_size = Path(source_path).stat().st_size
            
            # Add logging for detailed tracking
            logger.info(f"Verifying upload: {object_name}")
            logger.info(f"MinIO reported size: {stat.size}")
            logger.info(f"Source file size: {source_size}")
            
            # Robust size verification with some flexibility
            if abs(stat.size - source_size) > 1024:  # Allow 1KB variance
                logger.error(f"Size mismatch for {object_name}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Upload verification failed for {object_name}: {e}")
            return False

    async def process_video(self, video_id: str, source_path: str):
        """
        Process video asynchronously
        """
        logger.info(f"Starting video processing for {video_id}")
        
        try:
            # Run CPU-intensive processing in a separate process
            loop = asyncio.get_event_loop()
            success, error_message = await loop.run_in_executor(
                None,
                self._cpu_intensive_processing,
                video_id,
                source_path
            )

            if not success:
                raise Exception(error_message)

        except Exception as e:
            logger.error(f"Failed to process video {video_id}: {e}")
            raise
        finally:
            # Remove task from tracking
            if video_id in self.processing_tasks:
                del self.processing_tasks[video_id]
            
            # Clean up source file
            try:
                if os.path.exists(source_path):
                    os.unlink(source_path)
            except Exception as e:
                logger.error(f"Failed to clean up source file for {video_id}: {e}")

    def start_processing(self, video_id: str, source_path: str):
        """
        Start video processing in the background
        """
        # Create the background task
        task = asyncio.create_task(self.process_video(video_id, source_path))
        self.processing_tasks[video_id] = task
        
        # Add error handling callback
        def handle_task_result(task):
            try:
                task.result()
            except Exception as e:
                logger.error(f"Background task failed for video {video_id}: {e}")
        
        task.add_done_callback(handle_task_result)

    async def get_processing_status(self, video_id: str) -> str:
        """
        Get the current processing status of a video
        """
        if video_id in self.processing_tasks:
            task = self.processing_tasks[video_id]
            if task.done():
                try:
                    task.result()  # Will raise exception if task failed
                    return "completed"
                except Exception:
                    return "failed"
            return "processing"
        
        # Check if the HLS playlist exists in MinIO
        try:
            self.minio_client.stat_object(self.bucket_name, f"{video_id}/playlist.m3u8")
            return "completed"
        except:
            return "not_found"