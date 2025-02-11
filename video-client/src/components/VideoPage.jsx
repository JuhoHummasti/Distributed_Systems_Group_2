import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import VideoPlayer from "./VideoPlayer";

const VideoPage = () => {
  const { videoId } = useParams();
  const navigate = useNavigate();
  const [video, setVideo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchVideoDetails = async () => {
      try {
        const response = await fetch(
          `${
            import.meta.env.REQUEST_API_URL || "http://localhost:8080"
          }/videos/${videoId}`
        );
        if (!response.ok) {
          throw new Error("Failed to fetch video details");
        }
        const data = await response.json();
        const video = data[0];
        setVideo(video);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchVideoDetails();
  }, [videoId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-gray-600">Loading video...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-red-600">Error: {error}</div>
      </div>
    );
  }

  if (!video) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-gray-600">Video not found</div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen px-4 py-8">
      <button
        onClick={() => navigate(-1)}
        className="mb-4 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 transition"
      >
        Back to Videos
      </button>
      <div>
        <h1 className="text-2xl font-bold mb-2">{video.title}</h1>
        <p className="text-gray-600 mb-6">{video.description}</p>
        <VideoPlayer video_id={videoId} />
      </div>
    </div>
  );
};

export default VideoPage;
