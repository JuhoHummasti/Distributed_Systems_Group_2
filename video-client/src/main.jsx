import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import VideoStreamingApp from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <VideoStreamingApp />
  </StrictMode>
);
