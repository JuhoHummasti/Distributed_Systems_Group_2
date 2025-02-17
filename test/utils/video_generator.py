import cv2
import numpy as np

def generate_test_video(output_path, frame_count, frame_size=(640, 480), fps=30):
    """
    Generate a test MP4 video file with random content.
    
    Args:
        output_path (str): Path where the video file will be saved
        frame_count (int): Number of frames to generate
        frame_size (tuple): Width and height of the video frame (default: 640x480)
        fps (int): Frames per second (default: 30)
    
    Returns:
        bool: True if video generation was successful, False otherwise
    """
    try:
        # Define the codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, frame_size)
        
        for _ in range(frame_count):
            # Create a random frame
            frame = np.random.randint(0, 255, (frame_size[1], frame_size[0], 3), dtype=np.uint8)
            
            # Add some moving shapes
            cv2.circle(frame, 
                      (int(frame_size[0] * ((_ % fps) / fps)), frame_size[1] // 2),
                      30, (0, 255, 0), -1)
            
            # Write the frame
            out.write(frame)
        
        # Release the VideoWriter
        out.release()
        return True
        
    except Exception as e:
        print(f"Error generating video: {str(e)}")
        return False
