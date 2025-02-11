import { useState } from "react";
import { Upload, Loader, CheckCircle, XCircle } from "lucide-react";

const UploadForm = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("video/")) {
      setSelectedFile(file);
      setUploadStatus(null);
      setErrorMessage("");
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file && file.type.startsWith("video/")) {
      setSelectedFile(file);
      setUploadStatus(null);
      setErrorMessage("");
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadStatus(null);
    setErrorMessage("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch(
        `${import.meta.env.UPLOAD_API_URL || "http://localhost:8000"}/upload/`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      await response.json();
      setUploadStatus("success");
      setSelectedFile(null);
      // Reset file input
      const fileInput = document.getElementById("file-upload");
      if (fileInput) fileInput.value = "";
    } catch (error) {
      setUploadStatus("error");
      setErrorMessage(error.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto mt-8">
      {uploadStatus === "success" && (
        <div className="mb-4 p-4 rounded border border-green-200 bg-green-50 flex items-start">
          <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-green-800">Success</h3>
            <p className="text-sm text-green-700">
              Video uploaded successfully!
            </p>
          </div>
        </div>
      )}

      {uploadStatus === "error" && (
        <div className="mb-4 p-4 rounded border border-red-200 bg-red-50 flex items-start">
          <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Upload Failed</h3>
            <p className="text-sm text-red-700">
              {errorMessage || "An error occurred while uploading the video."}
            </p>
          </div>
        </div>
      )}

      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center ${
          isDragging ? "border-blue-500 bg-blue-50" : "border-gray-300"
        } ${isUploading ? "opacity-50 pointer-events-none" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <Upload className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-sm text-gray-600">
          Drag and drop your video here, or
        </p>
        <input
          type="file"
          accept="video/*"
          onChange={handleFileSelect}
          className="hidden"
          id="file-upload"
          disabled={isUploading}
        />
        <label
          htmlFor="file-upload"
          className={`mt-2 inline-block px-4 py-2 text-sm font-medium ${
            isUploading
              ? "text-gray-400 cursor-not-allowed"
              : "text-blue-600 hover:text-blue-500 cursor-pointer"
          }`}
        >
          Browse files
        </label>
        {selectedFile && (
          <div className="mt-4">
            <p className="text-sm text-gray-600">
              Selected: {selectedFile.name}
            </p>
          </div>
        )}
      </div>
      <button
        onClick={handleUpload}
        disabled={!selectedFile || isUploading}
        className={`mt-4 w-full py-2 px-4 rounded-md flex items-center justify-center ${
          !selectedFile || isUploading
            ? "bg-gray-300 text-gray-500 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-700 text-white"
        }`}
      >
        {isUploading ? (
          <>
            <Loader className="animate-spin mr-2 h-5 w-5" />
            Uploading...
          </>
        ) : (
          "Upload Video"
        )}
      </button>
    </div>
  );
};

export default UploadForm;
