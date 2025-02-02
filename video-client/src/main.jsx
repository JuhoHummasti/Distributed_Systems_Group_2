import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import VideoStreamingApp from "./App.jsx";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import VideoPage from "./components/VideoPage.jsx";
import VideoTest from "./components/VideoTest.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Router>
      <Routes>
        <Route path="/" element={<VideoStreamingApp />} />
        <Route path="/video/:videoId" element={<VideoPage />} />
        <Route path="/video_test/:videoId" element={<VideoTest />} />
      </Routes>
    </Router>
  </StrictMode>
);
