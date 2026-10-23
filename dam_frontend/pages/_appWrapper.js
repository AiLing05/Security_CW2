import dynamic from "next/dynamic";
import { ChakraProvider } from "@chakra-ui/react";
import theme from "../theme";

function MyAppWrapper({ Component, pageProps }) {
  if (typeof window !== "undefined") {
    // Ensure localStorage is ready before hydration
    const username = localStorage.getItem("username") || "Guest";
    const role = localStorage.getItem("role") || "User";
    if (!localStorage.getItem("username")) {
      localStorage.setItem("username", username);
      localStorage.setItem("role", role);
    }
  }

  return (
    <ChakraProvider theme={theme}>
      <Component {...pageProps} />
    </ChakraProvider>
  );
}

// Disable SSR for this wrapper so hydration happens only after localStorage exists
export default dynamic(() => Promise.resolve(MyAppWrapper), {
  ssr: false,
});
