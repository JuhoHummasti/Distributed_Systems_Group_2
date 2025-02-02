import VideoPlayer from "./VideoPlayer";
import { useParams } from "react-router-dom";

const VideoTest = () => {
  const { videoId } = useParams();
  return (
    <div className="w-screen h-screen flex justify-center items-center">
      <VideoPlayer video_id={videoId} />
    </div>
  );
};

export default VideoTest;
