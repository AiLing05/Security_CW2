import { useEffect } from "react";
import { useRouter } from "next/router";
import { isAuthenticated } from "../lib/browserSession";

export default function useAuthGuard() {
  const router = useRouter();
  useEffect(() => { if (!isAuthenticated()) router.replace("/login"); }, [router]);
}
