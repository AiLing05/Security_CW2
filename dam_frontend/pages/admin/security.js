import { useEffect, useState, useCallback } from "react";
import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  HStack,
  Input,
  Select,
  SimpleGrid,
  Spinner,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  VStack,
  useToast,
} from "@chakra-ui/react";
import { useRouter } from "next/router";
import Layout from "../../components/Layout";
import StatsCard from "../../components/StatsCard";
import { fetchWithToken } from "../../lib/api";

const SEVERITY_COLOR = { info: "gray", warning: "orange", high: "red", critical: "purple" };
const CATEGORIES = ["authentication", "authorization", "asset", "admin", "audit", "detection"];
const SERIES = [
  { key: "login_success", label: "Successful logins", color: "green.400" },
  { key: "login_failed", label: "Failed logins", color: "red.400" },
  { key: "access_denied", label: "Access denied", color: "orange.400" },
  { key: "alerts", label: "Alerts", color: "purple.500" },
];

function SeverityBadge({ value }) {
  return <Badge colorScheme={SEVERITY_COLOR[value] || "gray"}>{value}</Badge>;
}

// Simple grouped bar chart built from Chakra boxes (no extra chart dependency)
function TrendChart({ trend }) {
  const max = Math.max(1, ...trend.flatMap((d) => SERIES.map((s) => d[s.key])));
  return (
    <Box>
      <HStack align="end" spacing={4} h="180px" borderBottom="1px" borderColor="gray.200">
        {trend.map((day) => (
          <VStack key={day.date} flex={1} spacing={1} h="100%" justify="end">
            <HStack align="end" spacing="2px" h="100%">
              {SERIES.map((s) => (
                <Box
                  key={s.key}
                  w="10px"
                  h={`${(day[s.key] / max) * 100}%`}
                  minH={day[s.key] ? "2px" : 0}
                  bg={s.color}
                  borderTopRadius="sm"
                  title={`${s.label}: ${day[s.key]}`}
                />
              ))}
            </HStack>
          </VStack>
        ))}
      </HStack>
      <HStack spacing={4} mt={1}>
        {trend.map((day) => (
          <Text key={day.date} flex={1} fontSize="xs" color="gray.500" textAlign="center">
            {day.date.slice(5)}
          </Text>
        ))}
      </HStack>
      <HStack spacing={4} mt={3} wrap="wrap">
        {SERIES.map((s) => (
          <HStack key={s.key} spacing={1}>
            <Box w="10px" h="10px" bg={s.color} borderRadius="sm" />
            <Text fontSize="sm">{s.label}</Text>
          </HStack>
        ))}
      </HStack>
    </Box>
  );
}

export default function SecurityDashboard() {
  const router = useRouter();
  const toast = useToast();
  const [token, setToken] = useState(null);
  const [role, setRole] = useState(null);
  const [denied, setDenied] = useState(false);
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState({ count: 0, results: [] });
  const [integrity, setIntegrity] = useState(null);
  const [filters, setFilters] = useState({ category: "", severity: "", actor: "", page: 1 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = localStorage.getItem("access_token");
    const r = localStorage.getItem("role");
    if (!t) {
      router.push("/login");
      return;
    }
    setToken(t);
    setRole(r);
  }, []);

  const handleError = useCallback(
    (err) => {
      // The backend is the real access control; respect its answer.
      if (err && (err.status === 401 || err.status === 403)) {
        setDenied(true);
      } else {
        toast({ title: "Could not load security data", status: "error" });
      }
    },
    [toast]
  );

  const loadSummary = useCallback(async () => {
    try {
      setSummary(await fetchWithToken("/audit/summary/", token));
    } catch (err) {
      handleError(err);
    }
  }, [token, handleError]);

  const loadEvents = useCallback(async () => {
    const params = new URLSearchParams({ page: String(filters.page) });
    if (filters.category) params.set("category", filters.category);
    if (filters.severity) params.set("severity", filters.severity);
    if (filters.actor) params.set("actor", filters.actor);
    try {
      setEvents(await fetchWithToken(`/audit/events/?${params}`, token));
    } catch (err) {
      handleError(err);
    }
  }, [token, filters, handleError]);

  useEffect(() => {
    if (!token) return;
    if (role !== "admin") {
      setDenied(true);
      setLoading(false);
      return;
    }
    loadSummary().finally(() => setLoading(false));
  }, [token, role, loadSummary]);

  useEffect(() => {
    if (token && role === "admin") loadEvents();
  }, [token, role, loadEvents]);

  async function checkIntegrity() {
    try {
      setIntegrity(await fetchWithToken("/audit/integrity/", token));
    } catch (err) {
      handleError(err);
    }
  }

  if (denied) {
    return (
      <Layout>
        <Box p={8}>
          <Text color="red.500" fontWeight="bold">
            Access denied. The security dashboard is available to administrators only.
          </Text>
        </Box>
      </Layout>
    );
  }

  if (loading || !summary) {
    return (
      <Layout>
        <Box p={8} textAlign="center">
          <Spinner size="xl" />
          <Text mt={4}>Loading security data...</Text>
        </Box>
      </Layout>
    );
  }

  const t = summary.last_24h;
  const totalPages = Math.max(1, Math.ceil(events.count / 12));

  return (
    <Layout>
      <Flex align="center" mb={6}>
        <Heading size="lg">Security Monitoring</Heading>
        <Box flex={1} />
        <Button size="sm" mr={2} onClick={() => { loadSummary(); loadEvents(); }}>
          Refresh
        </Button>
        <Button size="sm" colorScheme="purple" onClick={checkIntegrity}>
          Verify audit integrity
        </Button>
      </Flex>

      {integrity && (
        <Box
          mb={6}
          p={4}
          borderRadius="md"
          bg={integrity.intact ? "green.50" : "red.50"}
          borderLeft="4px"
          borderColor={integrity.intact ? "green.400" : "red.500"}
        >
          {integrity.intact
            ? `Audit trail intact: ${integrity.records_checked} records verified against the hash chain.`
            : `Audit trail TAMPERED: first invalid record id ${integrity.first_invalid_id}.`}
        </Box>
      )}

      <Text fontSize="sm" color="gray.500" mb={2}>
        Last 24 hours
      </Text>
      <SimpleGrid columns={{ base: 2, md: 3, lg: 6 }} spacing={4} mb={8}>
        <StatsCard title="Events" value={t.total} />
        <StatsCard title="Logins" value={t.login_success} />
        <StatsCard title="Failed logins" value={t.login_failed} />
        <StatsCard title="Access denied" value={t.access_denied} />
        <StatsCard title="Rate limited" value={t.rate_limited} />
        <StatsCard title="Alerts" value={t.alerts} subtitle={`${t.high_severity} high+`} />
      </SimpleGrid>

      <SimpleGrid columns={{ base: 1, lg: 3 }} spacing={6} mb={8}>
        <Box gridColumn={{ lg: "span 2" }} p={5} bg="white" borderRadius="lg" boxShadow="md">
          <Heading size="sm" mb={4}>7-day security trend</Heading>
          <TrendChart trend={summary.trend_7d} />
        </Box>
        <Box p={5} bg="white" borderRadius="lg" boxShadow="md">
          <Heading size="sm" mb={3}>Top failure sources (24h)</Heading>
          {summary.top_failed_ips_24h.length === 0 && <Text color="gray.500">None</Text>}
          {summary.top_failed_ips_24h.map((row) => (
            <Flex key={row.ip_address} justify="space-between" py={1}>
              <Text fontFamily="mono">{row.ip_address}</Text>
              <Badge colorScheme="red">{row.count}</Badge>
            </Flex>
          ))}
          <Heading size="sm" mt={5} mb={3}>Most-targeted usernames (24h)</Heading>
          {summary.top_failed_usernames_24h.length === 0 && <Text color="gray.500">None</Text>}
          {summary.top_failed_usernames_24h.map((row) => (
            <Flex key={row.actor_username} justify="space-between" py={1}>
              <Text>{row.actor_username}</Text>
              <Badge colorScheme="orange">{row.count}</Badge>
            </Flex>
          ))}
        </Box>
      </SimpleGrid>

      <Box p={5} bg="white" borderRadius="lg" boxShadow="md" mb={8}>
        <Heading size="sm" mb={3}>Suspicious activity alerts</Heading>
        {summary.recent_alerts.length === 0 ? (
          <Text color="gray.500">No alerts raised.</Text>
        ) : (
          <Table size="sm">
            <Thead>
              <Tr><Th>Time</Th><Th>Alert</Th><Th>Severity</Th><Th>Details</Th></Tr>
            </Thead>
            <Tbody>
              {summary.recent_alerts.map((a) => (
                <Tr key={a.id}>
                  <Td whiteSpace="nowrap">{new Date(a.timestamp).toLocaleString()}</Td>
                  <Td>{a.event_label}</Td>
                  <Td><SeverityBadge value={a.severity} /></Td>
                  <Td>{a.target_repr}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        )}
      </Box>

      <Box p={5} bg="white" borderRadius="lg" boxShadow="md">
        <Heading size="sm" mb={3}>Audit log</Heading>
        <HStack mb={4} spacing={3}>
          <Select
            placeholder="All categories"
            value={filters.category}
            onChange={(e) => setFilters({ ...filters, category: e.target.value, page: 1 })}
          >
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </Select>
          <Select
            placeholder="All severities"
            value={filters.severity}
            onChange={(e) => setFilters({ ...filters, severity: e.target.value, page: 1 })}
          >
            {Object.keys(SEVERITY_COLOR).map((s) => <option key={s} value={s}>{s}</option>)}
          </Select>
          <Input
            placeholder="Username"
            value={filters.actor}
            onChange={(e) => setFilters({ ...filters, actor: e.target.value, page: 1 })}
          />
        </HStack>
        <Box overflowX="auto">
          <Table size="sm">
            <Thead>
              <Tr>
                <Th>Time</Th><Th>Event</Th><Th>Severity</Th><Th>User</Th>
                <Th>IP</Th><Th>Request</Th><Th>Target</Th>
              </Tr>
            </Thead>
            <Tbody>
              {events.results.map((e) => (
                <Tr key={e.id}>
                  <Td whiteSpace="nowrap">{new Date(e.timestamp).toLocaleString()}</Td>
                  <Td>{e.event_label}</Td>
                  <Td><SeverityBadge value={e.severity} /></Td>
                  <Td>{e.actor_username}{e.actor_role ? ` (${e.actor_role})` : ""}</Td>
                  <Td fontFamily="mono">{e.ip_address || "-"}</Td>
                  <Td fontFamily="mono" fontSize="xs">
                    {e.method} {e.path} {e.status_code || ""}
                  </Td>
                  <Td>{e.target_repr || (e.target_type ? `${e.target_type} #${e.target_id}` : "-")}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
        <Flex mt={4} align="center" justify="space-between">
          <Text fontSize="sm" color="gray.500">{events.count} events</Text>
          <HStack>
            <Button
              size="sm"
              isDisabled={filters.page <= 1}
              onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
            >
              Previous
            </Button>
            <Text fontSize="sm">{filters.page} / {totalPages}</Text>
            <Button
              size="sm"
              isDisabled={filters.page >= totalPages}
              onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
            >
              Next
            </Button>
          </HStack>
        </Flex>
      </Box>
    </Layout>
  );
}
