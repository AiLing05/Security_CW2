// dam_frontend/pages/index.js
import { useEffect } from "react";
import { useRouter } from "next/router";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/login"); // Redirect to /login
  }, [router]);

  return null; // Nothing is rendered while redirecting
}
