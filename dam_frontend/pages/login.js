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

import { apiFetch } from "../lib/apiFetch";
import { isAuthenticated, setSessionUser } from "../lib/browserSession";
import { useDispatch } from "react-redux";
import { loginSuccess } from "../redux/userSlice";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPw, setShowPw] = useState(false);
  const router = useRouter();
  const toast = useToast();
  const dispatch = useDispatch();

  // Redirect if already logged in
  useEffect(() => {
    const token =
      isAuthenticated();
    if (token) router.replace("/dashboard");
  }, [router]);

  async function onSubmit(e) {
    e.preventDefault();

    if (!username || !password) {
      toast({ title: "Please enter username and password.", status: "warning" });
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch("/api/token/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || "Invalid credentials");
      }

      const profile = await apiFetch("/api/me/");
      if (!profile.ok) throw new Error("Could not load your account.");
      const user = await profile.json();
      setSessionUser(user);
      dispatch(loginSuccess(user));

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
