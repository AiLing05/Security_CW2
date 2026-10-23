import { useRef, useState, useEffect } from "react";
import { Box, Text, Button, VStack, Spinner } from "@chakra-ui/react";

export default function UploadDropzone({ onFileSelected, preview }) {
  const inputRef = useRef();
  const [fileType, setFileType] = useState("unknown");
  const [isLoading, setIsLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // load model-viewer
  useEffect(() => {
    import("@google/model-viewer");
  }, []);

  const detectKind = (file) => {
    if (!file) return "unknown";
    const name = file.name?.toLowerCase();
    const type = file.type?.toLowerCase();

    if (type.startsWith("image/")) return "image";
    if (type.startsWith("video/")) return "video";
    if (/\.(glb|gltf|usdz|fbx|obj|stl)$/i.test(name)) return "model";

    return "unknown";
  };

  const handleFile = (file) => {
    if (!file) return;

    const kind = detectKind(file);
    setFileType(kind);
    onFileSelected(file);
    setIsLoading(kind === "model");
  };

  const handleFileChange = (e) => {
    handleFile(e.target.files[0]);
  };

  // 🔥 drag & drop handlers
  const onDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    handleFile(file);
  };

  // update preview type
  useEffect(() => {
    if (!preview) return;

    if (/\.(jpg|jpeg|png|webp|gif|bmp|svg)$/i.test(preview)) setFileType("image");
    else if (/\.(mp4|mov|avi|mkv)$/i.test(preview)) setFileType("video");
    else if (/\.(glb|gltf|usdz|fbx|obj|stl)$/i.test(preview)) setFileType("model");
  }, [preview]);

  return (
    <Box
      border="2px dashed"
      borderColor={isDragging ? "blue.400" : "gray.300"}
      bg={isDragging ? "blue.50" : "white"}
      p={6}
      rounded="md"
      textAlign="center"
      cursor="pointer"
      transition="0.2s"
      _hover={{ bg: "gray.50" }}
      onClick={() => inputRef.current?.click()}

      // ⬇️ Drag & drop events
      onDragOver={onDragOver}
      onDragEnter={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <VStack spacing={3}>
        {!preview ? (
          <Text color="gray.500">
            {isDragging ? "Drop your file here" : "Drag & drop, or click to upload"}
          </Text>
        ) : (
          <>
            {fileType === "image" && (
              <img
                src={preview}
                alt="Preview"
                style={{
                  maxWidth: "100%",
                  maxHeight: "250px",
                  objectFit: "contain",
                  borderRadius: "8px",
                }}
              />
            )}

            {fileType === "video" && (
              <video
                src={preview}
                controls
                style={{
                  maxWidth: "100%",
                  maxHeight: "250px",
                  borderRadius: "8px",
                }}
              />
            )}

            {fileType === "model" && (
              <Box position="relative" width="100%" height="300px">
                {isLoading && (
                  <Spinner
                    size="lg"
                    thickness="4px"
                    color="blue.400"
                    position="absolute"
                    top="50%"
                    left="50%"
                    transform="translate(-50%, -50%)"
                  />
                )}
                <model-viewer
                  src={preview}
                  camera-controls
                  auto-rotate
                  exposure="1"
                  environment-image="neutral"
                  onLoad={() => setIsLoading(false)}
                  style={{
                    width: "100%",
                    height: "300px",
                    background: "#f9fafb",
                    borderRadius: "10px",
                  }}
                />
              </Box>
            )}

            <Button size="sm" mt={2} onClick={() => inputRef.current?.click()}>
              Change File
            </Button>
          </>
        )}
      </VStack>

      <input
        type="file"
        ref={inputRef}
        onChange={handleFileChange}
        style={{ display: "none" }}
      />
    </Box>
  );
}
