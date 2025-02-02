import { useState } from "react";
import UploadForm from "./components/UploadForm";
import Tabs from "./components/Tabs";
import VideoGrid from "./components/VideoGrid";

const VideoStreamingApp = () => {
  const [activeTab, setActiveTab] = useState("upload");

  const tabs = [
    { id: "videos", label: "Videos" },
    { id: "upload", label: "Upload" },
  ];

  return (
    <div className="w-screen h-screen bg-gray-50 flex flex-col">
      <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="flex-1 p-4">
        {activeTab === "videos" ? (
          <div className="h-full flex justify-center">
            <VideoGrid />
          </div>
        ) : (
          <UploadForm />
        )}
      </div>
    </div>
  );
};

export default VideoStreamingApp;
