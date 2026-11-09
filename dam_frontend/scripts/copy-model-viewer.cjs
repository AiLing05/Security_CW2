// Serve the locked dependency locally in popup previews as well as the main app.
const { copyFileSync, mkdirSync } = require("node:fs");
const { join } = require("node:path");
const root = join(__dirname, "..");
const target = join(root, "public", "vendor");
mkdirSync(target, { recursive: true });
copyFileSync(join(root, "node_modules", "@google", "model-viewer", "dist", "model-viewer.min.js"), join(target, "model-viewer.min.js"));
copyFileSync(join(root, "node_modules", "@google", "model-viewer", "LICENSE"), join(target, "model-viewer.LICENSE"));
