import { useEffect } from "react";
import { useRouter } from "next/router";
import { useSelector } from "react-redux";

export default function useAuthGuard() {
  const router = useRouter();
  const { access } = useSelector((state) => state.user);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const token = access || localStorage.getItem("access_token");

    if (!token) {
      router.replace("/login");
    }
  }, [access, router]);
}
