import { ChakraProvider } from "@chakra-ui/react";
import { Provider } from "react-redux";
import dynamic from "next/dynamic";
import { store } from "../redux/store";
import theme from "../theme";
import useAuthInitializer from "../hooks/useAuthInitializer";

// ✅ Load <model-viewer> globally once
const ModelViewerLoader = dynamic(
  () => import("../components/ModelViewerLoader"),
  { ssr: false }
);

function AppContent({ Component, pageProps }) {
  const isReady = useAuthInitializer();

  if (!isReady) return null; // wait until user state is restored
  return <Component {...pageProps} />;
}

function MyApp({ Component, pageProps }) {
  return (
    <Provider store={store}>
      <ChakraProvider theme={theme}>
        {/* ✅ This loads the model-viewer web component safely */}
        <ModelViewerLoader />
        <AppContent Component={Component} pageProps={pageProps} />
      </ChakraProvider>
    </Provider>
  );
}

export default MyApp;
