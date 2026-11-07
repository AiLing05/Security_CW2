const api = process.env.DAM_INTERNAL_API_URL || "http://127.0.0.1:8000/api";
const url = new URL(api);
const localHTTP = url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
if ((url.protocol !== "https:" && !localHTTP) || url.username || url.password || url.search || url.hash || !/^\/api\/?$/.test(url.pathname)) {
  throw new Error("DAM_INTERNAL_API_URL must be an HTTPS API URL (HTTP is permitted only on loopback for development).");
}

module.exports = {
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Referrer-Policy", value: "same-origin" },
      { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
    ] }];
  },
};
