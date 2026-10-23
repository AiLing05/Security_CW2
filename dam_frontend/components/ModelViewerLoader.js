// components/ModelViewerLoader.js
import { useEffect } from "react";

export default function ModelViewerLoader() {
  useEffect(() => {
    // only register <model-viewer> once meaning will only load one time for the whole login
    if (!window.customElements.get("model-viewer")) {
      import("@google/model-viewer");
    }
  }, []);

  return null; // nothing to render
}
