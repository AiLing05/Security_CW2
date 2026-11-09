import { Box } from "@chakra-ui/react";
import NavBar from "../components/NavBar";

export default function Layout({ children }){
  return (
    <Box minH="100vh" bg="gray.50">
      <NavBar />
      <Box maxW="1200px" mx="auto" p={6}>{children}</Box>
      <Box as="footer" textAlign="center" p={4}>
        <a href="/security">Security and privacy guidance</a>
      </Box>
    </Box>
  );
}
