
import { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import { loginSuccess, logout } from "../redux/userSlice";

export default function useAuthInitializer() {
  const dispatch = useDispatch();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;

    try {
      const token = localStorage.getItem("access_token");
      const role = localStorage.getItem("role");
      const user = localStorage.getItem("user");

      if (token && role && user) {
        dispatch(
          loginSuccess({
            access: token,
            role,
            user: JSON.parse(user),
          })
        );
      } else {
        dispatch(logout());
      }
    } catch (err) {
      console.error("Auth init failed:", err);
      dispatch(logout());
    }

    setIsReady(true);
  }, [dispatch]);

  return isReady;
}
