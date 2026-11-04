const api = process.env.NEXT_PUBLIC_API_URL;
if (!api) throw new Error("Set NEXT_PUBLIC_API_URL before starting or building the frontend.");
const url = new URL(api);
const localHTTP = url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
if ((url.protocol !== "https:" && !localHTTP) || url.username || url.password || url.search || url.hash || !/^\/api\/?$/.test(url.pathname)) {
  throw new Error("NEXT_PUBLIC_API_URL must be an HTTPS API URL (HTTP is permitted only on loopback for development).");
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
