// pages/login.js
"use client";

import { useEffect, useState } from "react";
import {
  Box,
  Input,
  Button,
  Heading,
  VStack,
  Text,
  FormControl,
  FormLabel,
  InputGroup,
  InputRightElement,
  useToast,
} from "@chakra-ui/react";
import { useRouter } from "next/router";

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

/** ✅ Safe JWT decode (no external deps) */
function safeDecodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    const pad = payload.length % 4;
    const padded = payload + (pad ? "=".repeat(4 - pad) : "");
    const json = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decodeURIComponent(escape(json)));
  } catch {
    return null;
  }
}

/** ✅ Optional: fetch /me endpoint if role or username not inside token */
async function fetchUserInfo(access) {
  try {
    const res = await fetch(`${API_BASE}/me/`, {
      headers: { Authorization: `Bearer ${access}` },
    });
    if (!res.ok) return {};
    return await res.json();
  } catch {
    return {};
  }
}

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const router = useRouter();
  const toast = useToast();

  // Redirect if already logged in
  useEffect(() => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (token) router.replace("/dashboard");
  }, [router]);

  async function onSubmit(e) {
    e.preventDefault();

    if (!API_BASE) {
      toast({
        title: "Configuration error",
        description: "NEXT_PUBLIC_API_URL is not set.",
        status: "error",
      });
      return;
    }

    if (!username || !password) {
      toast({ title: "Please enter username and password.", status: "warning" });
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/token/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || "Invalid credentials");
      }

      const data = await res.json();
      const access = data.access;
      const refresh = data.refresh;
      if (!access) throw new Error("Token missing in response");

      // ✅ Store tokens
      localStorage.setItem("access_token", access);
      if (refresh) localStorage.setItem("refresh_token", refresh);

      // ✅ Decode JWT for username + role
      const decoded = safeDecodeJwt(access);
      let decodedUsername =
        decoded?.username ||
        decoded?.user?.username ||
        data?.username ||
        username;
      let role =
        decoded?.role ||
        decoded?.user?.role ||
        data?.role ||
        "";

      // ✅ Fallback to /me endpoint if missing
      if (!decodedUsername || !role) {
        const me = await fetchUserInfo(access);
        decodedUsername = decodedUsername || me.username || me.user?.username || username;
        role = role || me.role || me.user?.role || "";
      }

      // ✅ Save username + role for NavBar
      localStorage.setItem("username", decodedUsername);
      localStorage.setItem("role", role.toLowerCase());

      toast({
        title: "Signed in successfully.",
        status: "success",
        duration: 1500,
      });

      router.push("/dashboard");
    } catch (err) {
      console.error(err);
      toast({
        title: "Login failed",
        description: err?.message || "Check your credentials.",
        status: "error",
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box
      bgGradient="linear(to-br, #0B1020, #101735)"
      minH="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      px={4}
    >
      <Box bg="white" p={8} rounded="2xl" shadow="2xl" w="full" maxW="md">
        <Heading size="lg" textAlign="center" mb={1} color="blue.700">
          Digital Asset Manager
        </Heading>
        <Text fontSize="sm" color="gray.500" textAlign="center" mb={6}>
          Sign in to continue
        </Text>

        <form onSubmit={onSubmit}>
          <VStack spacing={4} align="stretch">
            <FormControl isRequired>
              <FormLabel>Username</FormLabel>
              <Input
                placeholder="Enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                size="md"
                focusBorderColor="blue.400"
                autoComplete="username"
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Password</FormLabel>
              <InputGroup>
                <Input
                  placeholder="Enter password"
                  type={showPw ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  size="md"
                  focusBorderColor="blue.400"
                  autoComplete="current-password"
                />
                <InputRightElement width="4.5rem">
                  <Button
                    h="1.75rem"
                    size="sm"
                    variant="ghost"
                    onClick={() => setShowPw((s) => !s)}
                  >
                    {showPw ? "Hide" : "Show"}
                  </Button>
                </InputRightElement>
              </InputGroup>
            </FormControl>

            <Button
              type="submit"
              colorScheme="blue"
              w="full"
              size="md"
              isLoading={loading}
            >
              Sign In
            </Button>

            <Text fontSize="sm" color="gray.500" textAlign="center">
              Contact your admin if you need access.
            </Text>
          </VStack>
        </form>
      </Box>
    </Box>
  );
}
