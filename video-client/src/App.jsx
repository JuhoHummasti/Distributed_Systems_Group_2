import { useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const VideoStreamingApp = () => {
  const [videoUrl, setVideoUrl] = useState(null);
  const [error, setError] = useState(null);

  const loadVideo = async (videoId) => {
    try {
      const response = await fetch(`${API_URL}/stream/${videoId}`);
      const data = await response.json();
      setVideoUrl(data.stream_url);
      setError(null);
    } catch (err) {
      setError("Error loading video");
      console.error(err);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      <div className="mb-4">
        <button
          onClick={() => loadVideo("1")}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Load Video 1
        </button>
      </div>

      {error && <div className="text-red-500 mb-4">{error}</div>}

      {videoUrl && (
        <div className="aspect-video bg-black rounded overflow-hidden">
          <video className="w-full h-full" controls autoPlay src={videoUrl}>
            Your browser does not support the video tag.
          </video>
        </div>
      )}
    </div>
  );
};

export default VideoStreamingApp;
