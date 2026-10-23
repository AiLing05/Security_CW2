// pages/admin/update-requests.js
import { useEffect, useState } from "react";
import {
  Box,
  Heading,
  Text,
  Button,
  Badge,
  Spinner,
  useToast,
  HStack,
  VStack,
  Divider,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  Stack,
} from "@chakra-ui/react";
import Layout from "../../components/Layout";
import { useRouter } from "next/router";

export default function UpdateRequests() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);
  const [role, setRole] = useState(null);
  const [previewVersion, setPreviewVersion] = useState(null);
  const [isOpen, setIsOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState("pending");
  const toast = useToast();
  const router = useRouter();

  const base = process.env.NEXT_PUBLIC_API_URL.replace("/api", "");

  useEffect(() => {
    const t = localStorage.getItem("access_token");
    const r = localStorage.getItem("role");

    if (!t) {
      router.push("/login");
      return;
    }

    setToken(t);
    setRole(r);

    if (r?.toLowerCase() === "admin") {
      fetchRequests(t);
    } else {
      toast({
        title: "Access Denied",
        description: "Only admins can view this page.",
        status: "error",
      });
      router.push("/dashboard");
    }
  }, []);

  async function fetchRequests(t) {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/versions/`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      const data = await res.json();
      const versionList = Array.isArray(data.results) ? data.results : Array.isArray(data) ? data : [];

      // Fetch full asset info for each version if missing
      const versionsWithAssets = await Promise.all(
        versionList.map(async (v) => {
          if (!v.asset && v.asset_id) {
            try {
              const resAsset = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/assets/${v.asset_id}/`, {
                headers: { Authorization: `Bearer ${t}` },
              });
              const assetData = await resAsset.json();
              return { ...v, asset: assetData };
            } catch (err) {
              console.error("Failed to fetch asset", err);
              return v;
            }
          }
          return v;
        })
      );

      setRequests(versionsWithAssets);
    } catch (err) {
      console.error(err);
      toast({ title: "Failed to fetch update requests", status: "error" });
      setRequests([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleApproval(id, approve = true) {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/versions/${id}/`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ status: approve ? "approved" : "rejected" }),
      });

      if (res.ok) {
        toast({
          title: approve ? "Request Approved" : "Request Rejected",
          status: approve ? "success" : "warning",
        });
        fetchRequests(token);
      } else {
        toast({ title: "Failed to update request", status: "error" });
      }
    } catch (err) {
      console.error(err);
      toast({ title: "Server error", status: "error" });
    }
  }

  const openPreview = (version) => {
    setPreviewVersion(version);
    setIsOpen(true);
  };

  const closePreview = () => {
    setPreviewVersion(null);
    setIsOpen(false);
  };

  if (loading) return <Spinner size="xl" />;

  // Group requests by status
  const groupedRequests = requests.reduce(
    (acc, req) => {
      const status = req.status || "pending";
      if (!acc[status]) acc[status] = [];
      acc[status].push(req);
      return acc;
    },
    { pending: [], approved: [], rejected: [] }
  );

  const renderRequestCard = (req) => (
    <Box key={req.id} p={5} borderWidth="1px" borderRadius="xl" shadow="sm" bg="white">
      <HStack justify="space-between" mb={2}>
        <Heading size="sm">{req.title || req.asset?.title || "Untitled"}</Heading>
        <Badge colorScheme={req.status === "approved" ? "green" : req.status === "rejected" ? "red" : "yellow"}>
          {req.status || "pending"}
        </Badge>
      </HStack>

      <Text fontSize="sm" color="gray.600">
        <b>Version:</b> {req.version_number || req.version || "-"}
      </Text>
      <Text fontSize="sm" color="gray.600">
        <b>Requested by:</b> {req.updated_by?.username || req.uploaded_by?.username || "Unknown"}
      </Text>
      <Text fontSize="sm" color="gray.600">
        <b>Date:</b> {req.updated_at ? new Date(req.updated_at).toLocaleString() :
          req.uploaded_at ? new Date(req.uploaded_at).toLocaleString() : "N/A"}
      </Text>

      <Divider my={3} />

      <HStack spacing={3}>
        <Button colorScheme="blue" size="sm" onClick={() => router.push(`/assets/${req.asset?.id || req.asset_id || ""}`)}>
          View Asset
        </Button>

        {req.status === "pending" && (
          <>
            <Button colorScheme="green" size="sm" onClick={() => handleApproval(req.id, true)}>Approve</Button>
            <Button colorScheme="red" size="sm" onClick={() => handleApproval(req.id, false)}>Reject</Button>
            <Button colorScheme="teal" size="sm" onClick={() => openPreview(req)}>Preview Changes</Button>
          </>
        )}
      </HStack>
    </Box>
  );

  return (
    <Layout>
      <Box p={8}>
        <Heading mb={4}>🔔 Update Requests</Heading>

        {/* Filter Bar */}
        <HStack spacing={4} mb={6} position="sticky" top={0} bg="white" zIndex={1} p={2} borderRadius="md" shadow="sm">
          {["pending", "approved", "rejected"].map((status) => (
            <Button
              key={status}
              size="sm"
              colorScheme={activeFilter === status ? "blue" : "gray"}
              variant={activeFilter === status ? "solid" : "outline"}
              onClick={() => setActiveFilter(status)}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </Button>
          ))}
        </HStack>

        {requests.length === 0 ? (
          <Box textAlign="center" py={10}>
            <Text color="gray.500" fontSize="lg">No update requests at the moment.</Text>
          </Box>
        ) : (
          <VStack align="stretch" spacing={5}>
            {groupedRequests[activeFilter].length > 0 ? (
              groupedRequests[activeFilter].map(renderRequestCard)
            ) : (
              <Text color="gray.500">No {activeFilter} requests.</Text>
            )}
          </VStack>
        )}

        {/* Preview Modal */}
        {previewVersion && (
          <Modal isOpen={isOpen} onClose={closePreview} size="xl">
            <ModalOverlay />
            <ModalContent>
              <ModalHeader>
                Preview Pending Changes (v{previewVersion.version_number || previewVersion.version || "-"})
              </ModalHeader>
              <ModalCloseButton />
              <ModalBody>
                <Text><b>Title:</b> {previewVersion.title || previewVersion.asset?.title || "Untitled"}</Text>
                <Text><b>Description:</b> {previewVersion.description}</Text>
                <Text><b>Category:</b> {previewVersion.category?.name || "Uncategorized"}</Text>
                <Text><b>Tags:</b> {previewVersion.tags?.map(t => t.name).join(", ") || "—"}</Text>

                {previewVersion.file ? (
                  /\.(jpg|jpeg|png|webp)$/i.test(previewVersion.file) ? (
                    <img
                      src={previewVersion.file.startsWith("http") ? previewVersion.file : `${base}${previewVersion.file}`}
                      alt="Preview"
                      style={{ maxHeight: "300px", display: "block", margin: "12px auto", borderRadius: "8px" }}
                    />
                  ) : previewVersion.file.endsWith(".mp4") ? (
                    <video
                      src={previewVersion.file.startsWith("http") ? previewVersion.file : `${base}${previewVersion.file}`}
                      controls
                      width="100%"
                      style={{ borderRadius: "12px", marginTop: "12px" }}
                    />
                  ) : (
                    <Text mt={3}>No file preview available.</Text>
                  )
                ) : (
                  <Text mt={3}>No file preview available.</Text>
                )}
              </ModalBody>
            </ModalContent>
          </Modal>
        )}
      </Box>
    </Layout>
  );
}
