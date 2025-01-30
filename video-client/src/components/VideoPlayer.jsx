import ReactHlsPlayer from "react-hls-player";

const VideoPlayer = () => {
  const videoUrl = "http://localhost:8000/stream/test.mp4/playlist.m3u8";

  return (
    <div className="w-full flex flex-col items-center min-h-screen bg-gray-100 p-6">
      <div className="w-full max-w-4xl bg-white rounded-lg shadow-lg p-6">
        <h1 className="text-2xl font-bold mb-4 text-gray-800">Video Player</h1>

        <div className="aspect-w-16 aspect-h-9 bg-black rounded-lg overflow-hidden">
          <ReactHlsPlayer
            src={videoUrl}
            autoPlay={false}
            controls={true}
            width="100%"
            height="auto"
            className="w-full h-full"
          />
        </div>

        <div className="mt-4 text-sm text-gray-600">
          <p>Stream ID: test</p>
          <p>Source: {videoUrl}</p>
        </div>
      </div>
    </div>
  );
};

export default VideoPlayer;
