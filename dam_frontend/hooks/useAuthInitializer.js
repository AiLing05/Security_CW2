import { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import { loginSuccess, logout } from "../redux/userSlice";
import { apiFetch } from "../lib/apiFetch";
import { isAuthenticated, setSessionUser } from "../lib/browserSession";

export default function useAuthInitializer() {
  const dispatch = useDispatch();
  const [isReady, setIsReady] = useState(false);
  useEffect(() => {
    let active = true;
    const expireSession = () => {
      const wasSignedIn = isAuthenticated();
      setSessionUser(null);
      dispatch(logout());
      if (wasSignedIn && window.location.pathname !== "/login") window.location.replace("/login");
    };
    window.addEventListener("dam:session-expired", expireSession);
    setSessionUser(null);
    apiFetch("/api/me/").then(async (response) => {
      if (!response.ok) throw new Error("Not signed in.");
      const user = await response.json();
      if (active) { setSessionUser(user); dispatch(loginSuccess(user)); }
    }).catch(() => {
      if (active) { setSessionUser(null); dispatch(logout()); }
    }).finally(() => { if (active) setIsReady(true); });
    return () => { active = false; window.removeEventListener("dam:session-expired", expireSession); };
  }, [dispatch]);
  return isReady;
}
