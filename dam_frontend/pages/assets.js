import { useEffect, useState } from "react";
import {
  Box, Heading, Input, Button, SimpleGrid, Text, VStack,
  FormControl, FormLabel, Textarea, Select, HStack,
  useToast, Divider
} from "@chakra-ui/react";
import { useRouter } from "next/router";
import Layout from "../components/Layout";
import UploadDropzone from "../components/UploadDropzone";

/*────────────────────────────────
 🔹 File Type Detection
────────────────────────────────*/
const detectKind = (name = "") => {
  const s = String(name).toLowerCase();
  if (!s) return "unknown";
  if (/\.(jpg|jpeg|png|webp|gif|bmp|svg)$/.test(s)) return "image";
  if (s.endsWith(".mp4")) return "video";
  if (s.endsWith(".pdf")) return "pdf";
  if (/\.(glb|gltf|usdz)$/.test(s)) return "model";
  return "unknown";
};

/*────────────────────────────────
 🔹 Open 3D Model in Fullscreen Tab
────────────────────────────────*/
async function openModelInNewTab({ srcUrl, token, title = "3D Preview" }) {
  try {
    let objectUrl = null;
    try {
      const res = await fetch(srcUrl, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("fetch failed");
      const blob = await res.blob();
      objectUrl = URL.createObjectURL(blob);
    } catch {
      objectUrl = srcUrl;
    }

    const w = window.open("", "_blank");
    if (!w) return;
    const safeTitle = (title || "3D Preview").replace(/</g, "&lt;");

    const html = `<!doctype html>
<html><head>
<meta charset="utf-8"/><title>${safeTitle}</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<script type="module" src="https://unpkg.com/@google/model-viewer@latest/dist/model-viewer.min.js"></script>
<style>
  html,body{height:100%;margin:0;background:#0b1020;color:#fff;font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial;}
  model-viewer{width:100vw;height:100vh;background:transparent;}
  .bar{position:fixed;inset:12px 12px auto 12px;display:flex;gap:10px;align-items:center;z-index:2}
  .ttl{font-weight:600;opacity:.9}
  .btn{border:1px solid #3b82f6;background:#1f2937;color:#fff;border-radius:10px;padding:8px 12px;cursor:pointer}
</style>
</head>
<body>
  <div class="bar"><span class="ttl">${safeTitle}</span>
    <button id="dl" class="btn">Download</button>
  </div>
  <model-viewer src="${objectUrl}" camera-controls auto-rotate environment-image="neutral" exposure="1"></model-viewer>
  <script>
    document.getElementById('dl').onclick=()=>{
      const a=document.createElement('a');
      a.href="${objectUrl}";
      a.download=${JSON.stringify(title || "model")};
      document.body.appendChild(a);a.click();a.remove();
    };
  </script>
</body></html>`;

    w.document.open();
    w.document.write(html);
    w.document.close();
  } catch {
    window.open(srcUrl, "_blank", "noopener,noreferrer");
  }
}

/*────────────────────────────────
 🔹 AssetCard Component (inline)
────────────────────────────────*/
function AssetCard({ asset }) {
  const router = useRouter();
  const base = process.env.NEXT_PUBLIC_API_URL?.replace("/api", "") || "";
  const fileUrl = asset.file?.startsWith("http") ? asset.file : `${base}${asset.file}`;
  const kind = detectKind(asset.file || "");

  return (
    <Box
      p={4}
      borderWidth="1px"
      borderRadius="md"
      shadow="sm"
      bg="white"
      _hover={{ shadow: "md" }}
    >
      <Heading size="md" mb={1}>
        {asset.title || "Untitled"}
      </Heading>
      <Text fontSize="sm" color="gray.600" noOfLines={2}>
        {asset.description || "No description available."}
      </Text>
      <Divider my={3} />
      <HStack justify="space-between">
        <Button
          colorScheme="blue"
          size="sm"
          onClick={() => router.push(`/assets/${asset.id}`)}
        >
          View Details
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => {
            const token = localStorage.getItem("access_token");
            if (kind === "model") {
              openModelInNewTab({
                srcUrl: fileUrl,
                token,
                title: asset.title || "3D Model",
              });
            } else {
              window.open(fileUrl, "_blank");
            }
          }}
        >
          Preview
        </Button>
      </HStack>
    </Box>
  );
}

/*────────────────────────────────
 🔹 Main Assets Page
────────────────────────────────*/
export default function AssetsPage() {
  const [assets, setAssets] = useState([]);
  const [token, setToken] = useState(null);
  const [role, setRole] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [customCategory, setCustomCategory] = useState("");
  const [tag, setTag] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [categories, setCategories] = useState([]);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("desc");
  const toast = useToast();

  const staticCategories = [
    "Images", "Videos", "Documents", "Audio", "Presentations",
    "Spreadsheets", "Animations", "Motion Graphics", "3D Models",
    "Archives", "Others",
  ];

  useEffect(() => {
    const t = localStorage.getItem("access_token");
    const r = localStorage.getItem("role");
    if (!t) return;
    setToken(t);
    setRole(r);
    fetchCategories(t).then(() => fetchAssets(t));
  }, [page, sort]);

  async function fetchAssets(t) {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/assets/?page=${page}&ordering=${sort === "asc" ? "created_at" : "-created_at"}`,
        { headers: { Authorization: `Bearer ${t}` } }
      );
      const data = await res.json();
      const normalizedAssets = Array.isArray(data)
        ? data
        : Array.isArray(data.results)
        ? data.results
        : [];
      setAssets(normalizedAssets);
    } catch (err) {
      console.error("Error fetching assets:", err);
      setAssets([]);
    }
  }

  async function fetchCategories(t) {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/categories/`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      const data = await res.json();
      const catList = Array.isArray(data.results) ? data.results : data;

      for (const name of staticCategories.filter(c => c !== "Others")) {
        if (!catList.some(c => c.name === name)) {
          await fetch(`${process.env.NEXT_PUBLIC_API_URL}/categories/`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${t}`,
            },
            body: JSON.stringify({ name }),
          });
        }
      }

      const updated = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/categories/`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      const finalCats = await updated.json();
      setCategories(Array.isArray(finalCats.results) ? finalCats.results : finalCats);
    } catch (err) {
      console.error("Error fetching categories:", err);
    }
  }

  async function handleUpload() {
    if (!selectedFile || !title) {
      toast({
        title: "Missing fields",
        description: "Please provide a title and select a file.",
        status: "warning",
      });
      return;
    }

    setIsUploading(true);
    try {
      let finalCategoryId = null;
      if (categoryId === "Others" && customCategory) {
        const categoryRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/categories/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ name: customCategory }),
        });
        if (!categoryRes.ok) throw new Error("Failed to create custom category");
        const newCat = await categoryRes.json();
        finalCategoryId = newCat.id;
      } else {
        const found = categories.find(c => c.name === categoryId);
        if (found) finalCategoryId = found.id;
      }

      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("title", title);
      formData.append("description", description);
      if (finalCategoryId) formData.append("category_id", finalCategoryId);
      if (tag) formData.append("tags", tag);

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/assets/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (res.ok) {
        toast({ title: "Upload successful", status: "success" });
        setSelectedFile(null);
        setPreview(null);
        setTitle("");
        setDescription("");
        setTag("");
        setCategoryId("");
        setCustomCategory("");
        fetchAssets(token);
      } else {
        const error = await res.text();
        console.error("Upload error:", error);
        toast({ title: "Upload failed", description: error, status: "error" });
      }
    } catch (err) {
      console.error(err);
      toast({ title: "Error during upload", description: err.message, status: "error" });
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <Layout>
      <Box px={6} py={4}>
        <Heading size="lg" mb={2}>Asset Management</Heading>
        <Text color="gray.500" mb={6}>
          Upload, preview, and manage your digital assets efficiently.
        </Text>

        <Divider mb={6} />

        {(role === "admin" || role === "editor") && (
          <Box bg="gray.50" p={6} rounded="xl" shadow="sm" mb={8}>
            <Heading size="md" mb={4}>Upload New Asset</Heading>
            <VStack align="stretch" spacing={4}>
              <FormControl>
                <FormLabel>Title</FormLabel>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Enter asset title" />
              </FormControl>
              <FormControl>
                <FormLabel>Description</FormLabel>
                <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Enter a short description" />
              </FormControl>
              <FormControl>
                <FormLabel>Category</FormLabel>
                <Select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} placeholder="Select category">
                  {staticCategories.map((cat) => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </Select>
              </FormControl>
              {categoryId === "Others" && (
                <FormControl>
                  <FormLabel>Custom Category</FormLabel>
                  <Input value={customCategory} onChange={(e) => setCustomCategory(e.target.value)} placeholder="Enter custom category" />
                </FormControl>
              )}
              <FormControl>
                <FormLabel>Tags</FormLabel>
                <Input value={tag} onChange={(e) => setTag(e.target.value)} placeholder="Comma-separated tags" />
              </FormControl>
              <FormControl>
                <FormLabel>File</FormLabel>
                <UploadDropzone
                  onFileSelected={(file) => {
                    setSelectedFile(file);
                    setPreview(URL.createObjectURL(file));
                  }}
                  preview={preview}
                />
              </FormControl>
              <Button colorScheme="blue" onClick={handleUpload} isLoading={isUploading}>
                Submit Asset
              </Button>
            </VStack>
          </Box>
        )}

        <Heading size="md" mb={4}>Uploaded Assets</Heading>
        {assets.length === 0 ? (
          <Text color="gray.500">No assets found.</Text>
        ) : (
          <SimpleGrid columns={[1, 2, 3]} spacing={6}>
            {assets.map((a) => (
              <AssetCard key={a.id} asset={a} />
            ))}
          </SimpleGrid>
        )}

        <HStack justify="center" mt={8} spacing={6}>
          <Button onClick={() => setPage((p) => Math.max(1, p - 1))} isDisabled={page === 1}>
            Previous
          </Button>
          <Text>Page {page}</Text>
          <Button onClick={() => setPage((p) => p + 1)}>Next</Button>
        </HStack>
      </Box>
    </Layout>
  );
}
