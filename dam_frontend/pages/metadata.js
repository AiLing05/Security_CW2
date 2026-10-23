// pages/metadata.js
import { useEffect, useState } from "react";
import {
  Box,
  Heading,
  Input,
  Select,
  Button,
  VStack,
  SimpleGrid,
  Text,
  HStack,
  FormControl,
  FormLabel,
  Spinner,
  Divider,
  useToast,
} from "@chakra-ui/react";
import Layout from "../components/Layout";
import AssetCard from "../components/AssetCard";

export default function MetadataSearchPage() {
  const [assets, setAssets] = useState([]);
  const [categories, setCategories] = useState([]);
  const [tags, setTags] = useState([]);
  const [token, setToken] = useState(null);
  const [role, setRole] = useState(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [tag, setTag] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const toast = useToast();
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    const t = localStorage.getItem("access_token");
    const r = localStorage.getItem("role");
    if (!t) return;
    setToken(t);
    setRole(r);
    fetchCategories(t);
    fetchTags(t);
    fetchAssets(t, page);
  }, [page]);

  async function fetchCategories(t) {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/categories/`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      const data = await res.json();
      setCategories(Array.isArray(data.results) ? data.results : data);
    } catch (err) {
      console.error(err);
    }
  }

  async function fetchTags(t) {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/tags/`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      const data = await res.json();
      setTags(Array.isArray(data.results) ? data.results : data);
    } catch (err) {
      console.error(err);
    }
  }

  async function fetchAssets(t, currentPage = 1) {
    setLoading(true);
    try {
      const queryParams = new URLSearchParams();
      if (query) queryParams.append("search", query);
      if (category) queryParams.append("category", category);
      if (tag) queryParams.append("tags", tag);
      if (dateFrom) queryParams.append("date_from", dateFrom);
      if (dateTo) queryParams.append("date_to", dateTo);
      queryParams.append("page", currentPage);

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/assets/?${queryParams.toString()}`,
        { headers: { Authorization: `Bearer ${t}` } }
      );
      const data = await res.json();

      // Safely extract results array
      const assetList = Array.isArray(data.results)
        ? data.results
        : Array.isArray(data)
        ? data
        : [];
      setAssets(assetList);

      // Optional: handle total pages if API returns pagination info
      if (data.count && data.results?.length) {
        setTotalPages(Math.ceil(data.count / data.results.length));
      } else {
        setTotalPages(1);
      }
    } catch (err) {
      console.error(err);
      toast({ title: "Failed to load assets", status: "error" });
      setAssets([]);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  }

  function handleSearch() {
    setPage(1); // reset to first page
    fetchAssets(token, 1);
  }

  return (
    <Layout>
      <Box px={6} py={6}>
        <Heading size="lg" mb={4}>
          Asset Metadata & Search
        </Heading>
        <Text color="gray.600" mb={6}>
          Search and manage digital assets by metadata, category, tags, or date range.
        </Text>

        <Box bg="gray.50" p={6} rounded="xl" shadow="sm" mb={6}>
          <VStack align="stretch" spacing={4}>
            <HStack spacing={4}>
              <FormControl>
                <FormLabel>Keyword</FormLabel>
                <Input
                  placeholder="Search by title or description"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </FormControl>

              <FormControl>
                <FormLabel>Category</FormLabel>
                <Select
                  placeholder="Select category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                >
                  {categories.map((cat) => (
                    <option key={cat.id} value={cat.id}>
                      {cat.name}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Tag</FormLabel>
                <Select
                  placeholder="Select tag"
                  value={tag}
                  onChange={(e) => setTag(e.target.value)}
                >
                  {tags.map((t) => (
                    <option key={t.id} value={t.name}>
                      {t.name}
                    </option>
                  ))}
                </Select>
              </FormControl>
            </HStack>

            <HStack spacing={4}>
              <FormControl>
                <FormLabel>Date From</FormLabel>
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
              </FormControl>
              <FormControl>
                <FormLabel>Date To</FormLabel>
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </FormControl>
            </HStack>

            <Button colorScheme="blue" onClick={handleSearch}>
              Search
            </Button>
          </VStack>
        </Box>

        <Divider mb={6} />

        <Heading size="md" mb={4}>
          Search Results
        </Heading>

        {loading ? (
          <Spinner size="lg" />
        ) : !Array.isArray(assets) || assets.length === 0 ? (
          <Text color="gray.500">No assets found.</Text>
        ) : (
          <SimpleGrid columns={[1, 2, 3]} spacing={5}>
            {assets.map((a) => (
              <AssetCard key={a.id} asset={a} />
            ))}
          </SimpleGrid>
        )}

        <HStack justify="center" mt={8} spacing={6}>
          <Button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            isDisabled={page === 1}
          >
            Previous
          </Button>
          <Text>
            Page {page} of {totalPages}
          </Text>
          <Button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            isDisabled={page === totalPages}
          >
            Next
          </Button>
        </HStack>
      </Box>
    </Layout>
  );
}
