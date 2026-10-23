"use client";

import { useRouter } from "next/router";
import { useEffect, useRef, useState } from "react";
import Script from "next/script";
import {
  Box, Heading, Text, Image, Button, VStack, HStack,
  Input, Textarea, Table, Thead, Tbody, Tr, Th, Td,
  useToast, Divider, Spinner, Badge, Modal, ModalOverlay,
  ModalContent, ModalHeader, ModalBody, ModalCloseButton,
  useDisclosure, Select,
} from "@chakra-ui/react";
import Layout from "../../components/Layout";

/* ---------------- helpers ---------------- */
const detectKind = (name = "") => {
  const s = String(name).toLowerCase();
  if (/\.(jpg|jpeg|png|webp|gif|bmp|svg)$/.test(s)) return "image";
  if (s.endsWith(".mp4") || s.endsWith(".webm")) return "video";
  if (s.endsWith(".pdf")) return "pdf";
  if (/\.(glb|gltf|usdz)$/.test(s)) return "model";
  return "unknown";
};

async function openModelInNewTab({ srcUrl, token, title = "3D Preview" }) {
  try {
    let objectUrl = srcUrl;
    try {
      const res = await fetch(srcUrl, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      if (!res.ok) throw new Error("fetch failed");
      const blob = await res.blob();
      objectUrl = URL.createObjectURL(blob);
    } catch {}
    const w = window.open("", "_blank", "noopener,noreferrer");
    if (!w) return;
    const safeTitle = String(title).replace(/</g, "&lt;");
    w.document.open();
    w.document.write(`<!doctype html>
<html><head><meta charset="utf-8"/><title>${safeTitle}</title>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<script type="module" src="https://unpkg.com/@google/model-viewer@latest/dist/model-viewer.min.js"></script>
<style>html,body{height:100%;margin:0;background:#0b1020}model-viewer{width:100vw;height:100vh}</style>
</head><body>
<model-viewer src="${objectUrl}" camera-controls auto-rotate environment-image="neutral" exposure="1"></model-viewer>
</body></html>`);
    w.document.close();
  } catch {
    window.open(srcUrl, "_blank", "noopener,noreferrer");
  }
}

export default function AssetDetails() {
  const router = useRouter();
  const { id } = router.query;

  const [asset, setAsset] = useState(null);
  const [versions, setVersions] = useState([]);
  const [categories, setCategories] = useState([]);

  const [token, setToken] = useState(null);
  const [role, setRole] = useState(null);

  const [isEditing, setIsEditing] = useState(false);
  const [updated, setUpdated] = useState({
    title: "", description: "", category_id: "", tags: "", file: null
  });
  const [localPreviewUrl, setLocalPreviewUrl] = useState(null);

  // used to force-refresh preview after updates (cache bust + rerender)
  const [cacheBust, setCacheBust] = useState(0);

  const [loading, setLoading] = useState(true);
  const [previewVersion, setPreviewVersion] = useState(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();

  const fileInputRef = useRef(null);

  const API = process.env.NEXT_PUBLIC_API_URL || "";
  const base = API ? API.replace("/api", "") : "";

  /* ---------- bootstrap ---------- */
  useEffect(() => {
    const t = localStorage.getItem("access_token");
    const r = localStorage.getItem("role");
    if (!t || !id) return;
    setToken(t); setRole(r);
    Promise.all([fetchAsset(t, id), fetchCategories(t), fetchVersions(t, id)])
      .catch(e => console.error(e))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    return () => { if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl); };
  }, [localPreviewUrl]);

  async function fetchCategories(t) {
    try {
      const r = await fetch(`${API}/categories/`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      const j = await r.json();
      const list = Array.isArray(j?.results) ? j.results : Array.isArray(j) ? j : [];
      setCategories(list);
    } catch (e) { console.error(e); }
  }

  async function fetchAsset(t, assetId) {
    const r = await fetch(`${API}/assets/${assetId}/`, {
      headers: { Authorization: `Bearer ${t}` },
    });
    if (!r.ok) throw new Error("asset fetch failed");
    const data = await r.json();
    setAsset(data);
    setUpdated({
      title: data.title || "",
      description: data.description || "",
      category_id: data.category?.id ?? data.category_id ?? "",
      tags: (Array.isArray(data.tags) ? data.tags.map(x=>x.name) : []).join(","),
      file: null,
    });
    if (localPreviewUrl) { URL.revokeObjectURL(localPreviewUrl); setLocalPreviewUrl(null); }
  }

  async function fetchVersions(t, assetId) {
    try {
      const r = await fetch(`${API}/versions/?asset_id=${assetId}`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      const j = await r.json();
      setVersions(Array.isArray(j?.results) ? j.results : Array.isArray(j) ? j : []);
    } catch (e) { console.error(e); }
  }

  /* ---------- save: editor requests, admin patches directly ---------- */
async function handleUpdate() {
  try {
    if (!token) return;

    const fd = new FormData();
    fd.append("title", updated.title ?? "");
    fd.append("description", updated.description ?? "");
    fd.append("tags", updated.tags ?? "");

    const catId = updated.category_id ? String(updated.category_id) : "";
    if (catId) {
      fd.append("category", catId);
      fd.append("category_id", catId);
    }
    if (updated.file) fd.append("file", updated.file);

    if (role === "editor") {
      if (!updated.file) {
        toast({ title: "Editors must attach a new file for update request.", status: "warning" });
        return;
      }
      const r = await fetch(`${API}/assets/${id}/request_update/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (!r.ok) throw new Error(await r.text());
      toast({ title: "Submitted for admin approval.", status: "success" });
    } else {
      const r = await fetch(`${API}/assets/${id}/`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      if (!r.ok) throw new Error(await r.text());
      toast({ title: "Asset updated.", status: "success" });
    }

    // reset editor state
    setIsEditing(false);
    setUpdated(u => ({ ...u, file: null }));
    if (localPreviewUrl) { URL.revokeObjectURL(localPreviewUrl); setLocalPreviewUrl(null); }
    setCacheBust(Date.now());

    // ✅ re-fetch the latest asset metadata
    const freshRes = await fetch(`${API}/assets/${id}/`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const freshAsset = await freshRes.json();
    setAsset(freshAsset);  // <--- this ensures frontend uses the latest file

    // fetch latest versions for version history
    await fetchVersions(token, id);
  } catch (e) {
    console.error(e);
    toast({ title: "Update failed", description: String(e.message || e), status: "error" });
  }
}


  async function handleDelete() {
    if (!confirm("Delete this asset?")) return;
    try {
      const r = await fetch(`${API}/assets/${id}/`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error(await r.text());
      toast({ title: "Asset deleted", status: "info" });
      router.push("/assets");
    } catch (e) {
      toast({ title: "Failed to delete", description: String(e), status: "error" });
    }
  }

  async function approveVersion(versionId, approve = true) {
    try {
      const r = await fetch(`${API}/versions/${versionId}/`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ status: approve ? "approved" : "rejected" }),
      });
      if (!r.ok) throw new Error(await r.text());
      toast({ title: approve ? "Approved" : "Rejected", status: approve ? "success" : "warning" });
      fetchVersions(token, id); fetchAsset(token, id);
    } catch (e) {
      toast({ title: "Failed to update version", description: String(e), status: "error" });
    }
  }

  if (!id || loading) {
    return (
      <Layout>
        <Box textAlign="center" py={20}>
          <Spinner size="xl" />
          <Text mt={3}>Loading asset details...</Text>
        </Box>
      </Layout>
    );
  }

  const filePath = asset?.file || "";
  const fullUrlRaw = filePath?.startsWith("http") ? filePath : `${base}${filePath}`;
  const fullUrl = cacheBust ? `${fullUrlRaw}${fullUrlRaw.includes("?") ? "&" : "?"}cb=${cacheBust}` : fullUrlRaw;
  const kind = detectKind(filePath);

  const categoryName =
    asset?.category?.name
    ?? (asset?.category_id ? categories.find(c => Number(c.id) === Number(asset.category_id))?.name : undefined)
    ?? "Uncategorized";

  return (
    <Layout>
      {/* model-viewer for 3D models */}

      <Box px={6} py={6}>
        <Heading mb={4}>Asset Details</Heading>

        <Box bg="gray.50" p={6} rounded="xl" shadow="md">
          <HStack align="start" spacing={8} flexWrap="wrap">
            {/* -------- Preview Column -------- */}
            <Box flex="1 1 380px" textAlign="center">
              <Heading size="sm" mb={2}>Current File Preview</Heading>
              <Box bg="gray.100" p={3} rounded="md" minH="320px" display="grid" placeItems="center">
                {!filePath ? (
                  <Text>No preview available</Text>
                ) : kind === "image" ? (
                  <Image key={`img-${cacheBust}`} src={fullUrl} alt={asset.title} maxH="300px" mx="auto" rounded="lg" shadow="sm" />
                ) : kind === "video" ? (
                  <video key={`vid-${cacheBust}`} src={fullUrl} controls width="100%" style={{ borderRadius: 12 }} />
                ) : kind === "pdf" ? (
                  <embed key={`pdf-${cacheBust}`} src={fullUrl} type="application/pdf" width="100%" height="300px" />
                ) : kind === "model" ? (
                  <model-viewer
                    key={`model-${cacheBust}`}
                    src={fullUrl}
                    camera-controls
                    auto-rotate
                    environment-image="neutral"
                    style={{ width: "100%", height: 300, borderRadius: 12, background: "transparent" }}
                  />
                ) : (
                  <Text>No preview available</Text>
                )}
              </Box>

              <HStack justify="center" mt={4} spacing={3}>
                <Button
                  colorScheme="blue"
                  onClick={() => {
                    if (kind === "model") {
                      openModelInNewTab({ srcUrl: fullUrlRaw, token, title: asset?.title || "3D Model" });
                    } else {
                      window.open(fullUrlRaw, "_blank", "noopener,noreferrer");
                    }
                  }}
                >
                  Open
                </Button>
                <Button
                  colorScheme="teal"
                  onClick={async () => {
                    try {
                      const r = await fetch(fullUrlRaw, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
                      if (!r.ok) throw new Error("download failed");
                      const b = await r.blob();
                      const u = URL.createObjectURL(b);
                      const a = document.createElement("a");
                      a.href = u; a.download = asset.title || "download";
                      document.body.appendChild(a); a.click(); a.remove();
                      URL.revokeObjectURL(u);
                    } catch (e) {
                      toast({ title: "Download failed", status: "error" });
                    }
                  }}
                >
                  Download
                </Button>
              </HStack>
            </Box>

            {/* -------- Metadata Column -------- */}
            <Box flex="1 1 380px">
              <Heading size="md" mb={3}>Metadata</Heading>

              {isEditing ? (
                <VStack align="stretch" spacing={3}>
                  <Input
                    bg="white"
                    value={updated.title}
                    onChange={(e) => setUpdated({ ...updated, title: e.target.value })}
                    placeholder="Title"
                  />
                  <Textarea
                    bg="white"
                    value={updated.description}
                    onChange={(e) => setUpdated({ ...updated, description: e.target.value })}
                    placeholder="Description"
                  />
                  <Select
                    bg="white"
                    placeholder="Select Category"
                    value={updated.category_id ?? ""}
                    onChange={(e) => setUpdated({ ...updated, category_id: Number(e.target.value) || "" })}
                  >
                    {categories.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </Select>
                  <Input
                    bg="white"
                    placeholder="Tags (comma separated)"
                    value={updated.tags}
                    onChange={(e) => setUpdated({ ...updated, tags: e.target.value })}
                  />

                  {/* Simple choose-file input (no drag & drop) */}
                  <Box>
                    <Text fontWeight="semibold" mb={2}>Upload New File (optional)</Text>
                    <HStack>
                      <Input
                        ref={fileInputRef}
                        type="file"
                        onChange={(e) => {
                          const f = e.target.files?.[0] || null;
                          setUpdated({ ...updated, file: f });
                          if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl);
                          setLocalPreviewUrl(f ? URL.createObjectURL(f) : null);
                        }}
                      />
                      {updated.file && (
                        <Button
                          variant="ghost"
                          colorScheme="red"
                          onClick={() => {
                            setUpdated({ ...updated, file: null });
                            if (localPreviewUrl) { URL.revokeObjectURL(localPreviewUrl); setLocalPreviewUrl(null); }
                            if (fileInputRef.current) fileInputRef.current.value = "";
                          }}
                        >
                          Clear
                        </Button>
                      )}
                    </HStack>

                    {/* file preview */}
                    {(updated.file || localPreviewUrl) && (
                      <Box mt={3} p={3} bg="gray.50" border="1px solid" borderColor="gray.200" rounded="lg">
                        <Text fontWeight="semibold" mb={2} noOfLines={1}>
                          {updated.file?.name || "New file selected"}
                        </Text>
                        {localPreviewUrl ? (
                          (() => {
                            const k = detectKind(updated.file?.name || "");
                            if (k === "image")
                              return <Image src={localPreviewUrl} alt="preview" maxH="240px" mx="auto" rounded="lg" shadow="sm" />;
                            if (k === "video")
                              return <video src={localPreviewUrl} controls style={{ width: "100%", borderRadius: 12 }} />;
                            if (k === "pdf")
                              return <embed src={localPreviewUrl} type="application/pdf" width="100%" height="240px" />;
                            if (k === "model")
                              return (
                                <model-viewer
                                  src={localPreviewUrl}
                                  camera-controls
                                  auto-rotate
                                  environment-image="neutral"
                                  style={{ width: "100%", height: 260, background: "transparent", borderRadius: 12 }}
                                />
                              );
                            return <Text color="gray.600">No inline preview for this file type.</Text>;
                          })()
                        ) : null}
                        <Text mt={2} fontSize="xs" color="gray.500">
                          Tip: leave empty to keep the current file unchanged.
                        </Text>
                      </Box>
                    )}
                  </Box>

                  <HStack>
                    <Button colorScheme="green" onClick={handleUpdate}>Save Changes</Button>
                    <Button variant="ghost" onClick={() => setIsEditing(false)}>Cancel</Button>
                  </HStack>
                </VStack>
              ) : (
                <>
                  <Text><b>Title:</b> {asset.title}</Text>
                  <Text><b>Description:</b> {asset.description || "—"}</Text>
                  <Text><b>Uploader:</b> {asset.uploaded_by?.username || "N/A"}</Text>
                  <Text><b>Category:</b> {categoryName}</Text>
                  <Text><b>Tags:</b> {asset.tags?.map(t => t.name).join(", ") || "—"}</Text>
                  <Text><b>Uploaded:</b> {asset.uploaded_at ? new Date(asset.uploaded_at).toLocaleString() : "—"}</Text>

                  {(role === "admin" || role === "editor") && (
                    <Button mt={4} colorScheme="teal" onClick={() => setIsEditing(true)}>Edit Metadata</Button>
                  )}
                  {role === "admin" && (
                    <Button mt={4} colorScheme="red" onClick={handleDelete}>Delete Asset</Button>
                  )}
                </>
              )}
            </Box>
          </HStack>

          {/* -------- Version History -------- */}
          {versions.length > 0 && (
            <>
              <Divider my={6} />
              <Heading size="md" mb={3}>Version History</Heading>
              <Table variant="simple">
                <Thead>
                  <Tr>
                    <Th>Version</Th>
                    <Th>Updated By</Th>
                    <Th>Date</Th>
                    <Th>Status</Th>
                    {role === "admin" && <Th>Actions</Th>}
                  </Tr>
                </Thead>
                <Tbody>
                  {versions.map(v => (
                    <Tr key={v.id}>
                      <Td>{v.version}</Td>
                      <Td>{v.uploaded_by?.username || "N/A"}</Td>
                      <Td>{new Date(v.uploaded_at).toLocaleString()}</Td>
                      <Td>
                        <Badge colorScheme={v.status === "approved" ? "green" : v.status === "pending" ? "yellow" : "red"}>
                          {v.status}
                        </Badge>
                      </Td>
                      <Td>
                        <HStack spacing={2}>
                          <Button size="sm" colorScheme="blue" onClick={() => { setPreviewVersion(v); onOpen(); }}>View</Button>
                          {role === "admin" && v.status === "pending" && (
                            <>
                              <Button size="sm" colorScheme="green" onClick={() => approveVersion(v.id, true)}>Approve</Button>
                              <Button size="sm" colorScheme="red" onClick={() => approveVersion(v.id, false)}>Reject</Button>
                            </>
                          )}
                        </HStack>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </>
          )}

          {/* -------- Modal Preview -------- */}
          {previewVersion && (
            <Modal isOpen={isOpen} onClose={() => { onClose(); setPreviewVersion(null); }} size="xl">
              <ModalOverlay />
              <ModalContent>
                <ModalHeader>Preview Pending Changes (v{previewVersion.version})</ModalHeader>
                <ModalCloseButton />
                <ModalBody>
                  <VStack align="stretch" spacing={2}>
                    <Text><b>Title:</b> {previewVersion.title || "—"}</Text>
                    <Text><b>Description:</b> {previewVersion.description || "—"}</Text>
                    <Text><b>Category:</b> {previewVersion.category?.name || "Uncategorized"}</Text>
                    <Text><b>Tags:</b> {previewVersion.tags?.map(t => t.name).join(", ") || "—"}</Text>
                  </VStack>
                  {previewVersion.file && (() => {
                    const pvRaw = previewVersion.file.startsWith("http") ? previewVersion.file : `${base}${previewVersion.file}`;
                    const pvUrl = cacheBust ? `${pvRaw}${pvRaw.includes("?") ? "&" : "?"}cb=${cacheBust}` : pvRaw;
                    const k = detectKind(previewVersion.file);
                    if (k === "image")
                      return <Image src={pvUrl} maxH="300px" mx="auto" mt={3} rounded="lg" shadow="sm" />;
                    if (k === "video")
                      return <video src={pvUrl} controls width="100%" style={{ borderRadius: 12, marginTop: 12 }} />;
                    if (k === "pdf")
                      return <embed src={pvUrl} type="application/pdf" width="100%" height="300px" />;
                    if (k === "model")
                      return (
                        <model-viewer
                          src={pvUrl}
                          camera-controls
                          auto-rotate
                          environment-image="neutral"
                          style={{ width: "100%", height: 300, borderRadius: 12, background: "transparent", marginTop: 12 }}
                        />
                      );
                    return <Text mt={3}>No file preview available.</Text>;
                  })()}
                </ModalBody>
              </ModalContent>
            </Modal>
          )}
        </Box>
      </Box>
    </Layout>
  );
}
