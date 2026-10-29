// components/NavBar.js
import {useState, useEffect} from "react";
import {Box, Flex, Button, Text, Spacer, Spinner} from "@chakra-ui/react";
import {useRouter} from "next/router";

const API_BASE =
    process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export default function NavBar() {
    const router = useRouter();

    // State for username, role, and client readiness
    const [isClient, setIsClient] = useState(false);
    const [username, setUsername] = useState("");
    const [role, setRole] = useState("");

    useEffect(() => {
        setIsClient(true); // Marks that we’re on the browser

        if (typeof window !== "undefined") {
            const storedUser = localStorage.getItem("username") || "Guest";
            const storedRole = localStorage.getItem("role") || "User";
            setUsername(storedUser);
            setRole(storedRole);
        }
    }, []);

    // Avoiding SSR hydration errors by not rendering until client is ready
    if (!isClient) {
        return (
            <Flex
                bg="white"
                boxShadow="sm"
                px={6}
                py={3}
                align="center"
                justify="center"
            >
                <Spinner size="sm" color="purple.500"/>
            </Flex>
        );
    }

    const isAdmin = role.toLowerCase() === "admin";


    const handleLogout = async () => {
        const access = localStorage.getItem("access_token");
        const refresh = localStorage.getItem("refresh_token");

        if (!access || !refresh) {
            localStorage.clear();
            router.replace("/login");
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/logout/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${access}`,
                },
                body: JSON.stringify({refresh}),
            });

            if (!response.ok) {
                throw new Error(`Logout failed: HTTP ${response.status}`);
            }

            localStorage.clear();
            router.replace("/login");
        } catch (error) {
            console.error("Server-side logout failed:", error);
            alert(
                "Secure logout could not be completed. Please retry. Your session may still be active."
            );
        }
    };


    return (
        <Box bg="white" boxShadow="sm" px={6} py={3}>
            <Flex align="center">
                <Text fontWeight="bold" fontSize="lg">
                    DAM System
                </Text>
                <Spacer/>

                {/* Main navigation links */}
                <Button variant="ghost" onClick={() => router.push("/dashboard")}>
                    Dashboard
                </Button>
                <Button variant="ghost" onClick={() => router.push("/assets")}>
                    Assets
                </Button>
                <Button variant="ghost" onClick={() => router.push("/metadata")}>
                    Metadata
                </Button>

                {/* Admin-only links */}
                {isAdmin && (
                    <>
                        <Button
                            variant="ghost"
                            onClick={() => router.push("/admin/update-requests")}
                        >
                            Update Requests
                        </Button>
                        <Button variant="ghost" onClick={() => router.push("/admin/users")}>
                            Manage Users
                        </Button>
                        <Button variant="ghost" onClick={() => router.push("/admin/security")}>
                            Security
                        </Button>
                    </>
                )}

                <Spacer/>
                <Text mr={4} fontSize="sm" color="gray.600">
                    {username} ({role})
                </Text>

                <Button
                    size="sm"
                    colorScheme="red"
                    variant="outline"
                    onClick={handleLogout}
                >
                    Logout
                </Button>
            </Flex>
        </Box>
    );
}
