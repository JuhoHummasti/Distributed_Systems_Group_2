import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const VideoGrid = () => {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        const response = await fetch(
          `${
            import.meta.env.VITE_REQUEST_API_URL || "http://localhost:8080"
          }/videos`
        );
        if (!response.ok) {
          throw new Error("Failed to fetch videos");
        }
        const data = await response.json();
        setVideos(data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchVideos();
  }, []);

  const handleVideoClick = (videoId) => {
    navigate(`/video/${videoId}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-gray-600">Loading videos...</div>
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

  if (!videos.length) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-gray-600">No videos found</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
        {videos.map((video) => (
          <div
            key={video.video_id}
            className="flex flex-col bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow duration-300 cursor-pointer"
            onClick={() => handleVideoClick(video.video_id)}
          >
            <div className="relative pt-[56.25%]">
              <img
                src={video.thumbnail_url}
                alt={video.title}
                className="absolute top-0 left-0 w-full h-full object-cover"
              />
            </div>
            <div className="p-4">
              <h3 className="text-sm font-medium text-gray-900 line-clamp-2">
                {video.title}
              </h3>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default VideoGrid;
