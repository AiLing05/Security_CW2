"use client";

import { Box, Text, Button, Heading, Divider, HStack, Image } from "@chakra-ui/react";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import { fetchProtectedFile } from "../utils/protectedFiles";

// Detect file type
const detectKind = (name = "") => {
  const s = String(name).toLowerCase();
  if (!s) return "unknown";
  if (/\.(jpg|jpeg|png|webp|gif|bmp|svg)$/.test(s)) return "image";
  if (s.endsWith(".mp4") || s.endsWith(".webm")) return "video";
  if (s.endsWith(".pdf")) return "pdf";
  if (/\.(glb|gltf|usdz)$/.test(s)) return "model";
  return "unknown";
};

// Open 3D model in new tab
async function openModelInNewTab({ srcUrl, token, title = "3D Preview" }) {
  try {
    let objectUrl = srcUrl;
    try {
      const res = await fetch(srcUrl, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      if (!res.ok) throw new Error("fetch failed");
      const blob = await res.blob();
      objectUrl = URL.createObjectURL(blob);
    } catch {}

    const w = window.open("", "_blank");
    if (!w) return;
    const safeTitle = (title || "3D Preview").replace(/</g, "&lt;");
    w.document.write(`<!doctype html>
<html><head><meta charset="utf-8"><title>${safeTitle}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<script type="module" src="https://unpkg.com/@google/model-viewer@latest/dist/model-viewer.min.js"></script>
<style>html,body{margin:0;height:100%;}model-viewer{width:100vw;height:100vh;}</style>
</head><body>
<model-viewer src="${objectUrl}" camera-controls auto-rotate environment-image="neutral"></model-viewer>
</body></html>`);
    w.document.close();
  } catch {
    window.open(srcUrl, "_blank", "noopener,noreferrer");
  }
}

export default function AssetCard({ asset: initialAsset, assetId }) {
  const router = useRouter();
  const base = process.env.NEXT_PUBLIC_API_URL?.replace("/api", "") || "";
  const [asset, setAsset] = useState(initialAsset || null);
  const [loading, setLoading] = useState(!initialAsset);
  const [protectedUrl, setProtectedUrl] = useState(null);

  // Fetch latest asset from backend if no full asset is passed
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (asset || !assetId || !token) return;

    setLoading(true);
    fetch(`${base}/api/assets/${assetId}/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setAsset(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [asset, assetId, base]);

  // Load asset preview using JWT authentication.
  useEffect(() => {
    if (!asset?.id) return;

    const token = localStorage.getItem("access_token");
    if (!token) return;

    let active = true;
    let objectUrl = null;

    setProtectedUrl(null);

    fetchProtectedFile(
      `${process.env.NEXT_PUBLIC_API_URL}/assets/${asset.id}/file/`,
      token
    )
      .then((url) => {
        objectUrl = url;

        if (active) {
          setProtectedUrl(url);
        } else {
          URL.revokeObjectURL(url);
        }
      })
      .catch((error) => {
        if (active) {
          console.error("Dashboard preview error:", error);
        }
      });

    return () => {
      active = false;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [asset?.id, asset?.file]);

  if (loading || !asset) return <Box>Loading...</Box>;

  const kind = detectKind(asset.file || "");

  return (
    <Box p={4} borderWidth="1px" borderRadius="md" shadow="sm" bg="white" _hover={{ shadow: "md" }}>
      <Heading size="md" mb={1}>{asset.title || "Untitled"}</Heading>
      <Text fontSize="sm" color="gray.600" noOfLines={2}>{asset.description || "No description available."}</Text>
      <Divider my={3} />

      {kind === "image" && protectedUrl && (
        <Image
          src={protectedUrl}
          alt={asset.title}
          mb={3}
          maxH="200px"
          objectFit="cover"
          borderRadius="md"
        />
      )}

      {kind === "video" && protectedUrl && (
        <video
          src={protectedUrl}
          controls
          style={{
            width: "100%",
            borderRadius: 12,
            marginBottom: 12,
          }}
        />
      )}

      {kind === "pdf" && protectedUrl && (
        <embed
          src={protectedUrl}
          type="application/pdf"
          width="100%"
          height="200px"
          style={{
            borderRadius: 12,
            marginBottom: 12,
          }}
        />
      )}

      {kind === "model" && protectedUrl && (
        <model-viewer
          src={protectedUrl}
          camera-controls
          auto-rotate
          environment-image="neutral"
          style={{
            width: "100%",
            height: 300,
            borderRadius: 12,
            background: "transparent",
            marginBottom: 12,
          }}
        />
      )}

      <HStack justify="space-between">
        <Button colorScheme="blue" size="sm" onClick={() => router.push(`/assets/${asset.id}`)}>View Details</Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            if (!protectedUrl) {
              alert("The file is still loading. Please try again.");
              return;
            }

            const token = localStorage.getItem("access_token");

            if (kind === "model") {
              openModelInNewTab({
                srcUrl: protectedUrl,
                token,
                title: asset.title || "3D Model",
              });
            } else {
              window.open(protectedUrl, "_blank", "noopener,noreferrer");
            }
          }}
        >
          Preview
        </Button>
      </HStack>
    </Box>
  );
}
