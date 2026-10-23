import { useState, useEffect } from "react";
import {
  Box,
  Heading,
  VStack,
  Input,
  FormControl,
  FormLabel,
  Select,
  Button,
  useToast,
  Text,
  Spinner,
  Divider,
  HStack,
} from "@chakra-ui/react";
import Layout from "../../components/Layout";
import { useRouter } from "next/router";

export default function UserManagement() {
  const router = useRouter();
  const [token, setToken] = useState(null);
  const [role, setRole] = useState(null);
  const [users, setUsers] = useState([]); // ✅ safe default
  const [loading, setLoading] = useState(true);
  const [editingUser, setEditingUser] = useState(null);
  const [form, setForm] = useState({
    username: "",
    first_name: "",
    last_name: "",
    email: "",
    password: "",
    role: "",
  });

  const toast = useToast();

  // ✅ Fetch auth details & users
  useEffect(() => {
    const t = localStorage.getItem("access_token");
    const r = localStorage.getItem("role");
    if (!t) {
      router.push("/login");
      return;
    }
    setToken(t);
    setRole(r);
    if (r === "admin") fetchUsers(t);
    else setLoading(false);
  }, []);

  // ✅ Fetch users
  async function fetchUsers(t) {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (!res.ok) throw new Error("Failed to fetch users");
      const data = await res.json();
      setUsers(Array.isArray(data.results) ? data.results : data); // ✅ prevent .map crash
    } catch (err) {
      console.error(err);
      toast({ title: "Failed to load users", status: "error" });
      setUsers([]); // ✅ safe fallback
    } finally {
      setLoading(false);
    }
  }

  // ✅ Save (Create/Update) user
  async function handleSaveUser() {
    if (!form.username || !form.role) {
      toast({ title: "Please fill all required fields", status: "warning" });
      return;
    }

    const url = editingUser
      ? `${process.env.NEXT_PUBLIC_API_URL}/users/${editingUser.id}/`
      : `${process.env.NEXT_PUBLIC_API_URL}/users/`;
    const method = editingUser ? "PUT" : "POST";

    try {
      const res = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      if (res.ok) {
        toast({
          title: editingUser ? "User updated successfully" : "User created successfully",
          status: "success",
        });
        resetForm();
        fetchUsers(token);
      } else {
        const err = await res.json();
        toast({
          title: "Error saving user",
          description: JSON.stringify(err),
          status: "error",
        });
      }
    } catch (err) {
      console.error(err);
      toast({ title: "Server error", status: "error" });
    }
  }

  // ✅ Delete user
  async function handleDeleteUser(id) {
    if (!confirm("Are you sure you want to delete this user?")) return;
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/${id}/`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        toast({ title: "User deleted", status: "info" });
        fetchUsers(token);
      } else {
        toast({ title: "Failed to delete user", status: "error" });
      }
    } catch (err) {
      console.error(err);
      toast({ title: "Failed to delete user", status: "error" });
    }
  }

  // ✅ Edit mode
  function handleEditUser(u) {
    setEditingUser(u);
    setForm({
      username: u.username,
      first_name: u.first_name || "",
      last_name: u.last_name || "",
      email: u.email || "",
      password: "",
      role: u.role || "",
    });
  }

  function resetForm() {
    setForm({
      username: "",
      first_name: "",
      last_name: "",
      email: "",
      password: "",
      role: "",
    });
    setEditingUser(null);
  }

  // ✅ Access restriction
  if (role && role !== "admin") {
    return (
      <Layout>
        <Box p={8}>
          <Text color="red.500" fontWeight="bold">
            Access denied. Admins only.
          </Text>
        </Box>
      </Layout>
    );
  }

  if (loading) {
    return (
      <Layout>
        <Box p={8} textAlign="center">
          <Spinner size="xl" />
          <Text mt={4}>Loading users...</Text>
        </Box>
      </Layout>
    );
  }

  // ✅ Main UI
  return (
    <Layout>
      <Box p={8}>
        <Heading mb={6}>👤 User Management</Heading>

        {/* User Form */}
        <Box bg="gray.50" p={6} rounded="xl" shadow="md">
          <Heading size="md" mb={4}>
            {editingUser ? "Edit User" : "Create New User"}
          </Heading>
          <VStack spacing={4} align="stretch">
            <FormControl isRequired>
              <FormLabel>Username</FormLabel>
              <Input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
              />
            </FormControl>

            <FormControl>
              <FormLabel>First Name</FormLabel>
              <Input
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              />
            </FormControl>

            <FormControl>
              <FormLabel>Last Name</FormLabel>
              <Input
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              />
            </FormControl>

            <FormControl>
              <FormLabel>Email</FormLabel>
              <Input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </FormControl>

            <FormControl>
              <FormLabel>Password</FormLabel>
              <Input
                type="password"
                placeholder={editingUser ? "Enter new or existing password" : ""}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </FormControl>

            <FormControl isRequired>
              <FormLabel>Role</FormLabel>
              <Select
                placeholder="Select role"
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
              >
                <option value="admin">Admin</option>
                <option value="editor">Editor</option>
                <option value="viewer">Viewer</option>
              </Select>
            </FormControl>

            <HStack>
              <Button colorScheme="blue" onClick={handleSaveUser}>
                {editingUser ? "Save Changes" : "Create User"}
              </Button>
              {editingUser && (
                <Button variant="ghost" onClick={resetForm}>
                  Cancel
                </Button>
              )}
            </HStack>
          </VStack>
        </Box>

        <Divider my={8} />

        {/* Existing Users */}
        <Heading size="md" mb={4}>
          Existing Users
        </Heading>
        {Array.isArray(users) && users.length > 0 ? (
          <VStack align="stretch" spacing={3}>
            {users.map((u) => (
              <Box
                key={u.id || u.username}
                p={4}
                bg="white"
                shadow="sm"
                rounded="md"
                borderWidth="1px"
              >
                <Text>
                  <b>Username:</b> {u.username}
                </Text>
                <Text>
                  <b>Email:</b> {u.email || "—"}
                </Text>
                <Text>
                  <b>Role:</b> {u.role || "N/A"}
                </Text>

                <HStack mt={2}>
                  <Button size="sm" colorScheme="teal" onClick={() => handleEditUser(u)}>
                    Edit
                  </Button>
                  <Button
                    size="sm"
                    colorScheme="red"
                    onClick={() => handleDeleteUser(u.id)}
                  >
                    Delete
                  </Button>
                </HStack>
              </Box>
            ))}
          </VStack>
        ) : (
          <Text color="gray.500">No users found.</Text>
        )}
      </Box>
    </Layout>
  );
}
