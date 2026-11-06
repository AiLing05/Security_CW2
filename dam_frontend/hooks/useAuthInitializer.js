import {useEffect, useState} from "react";
import {useDispatch} from "react-redux";
import {loginSuccess, logout} from "../redux/userSlice";

export default function useAuthInitializer() {
    const dispatch = useDispatch();
    const [isReady, setIsReady] = useState(false);

    useEffect(() => {
        if (typeof window === "undefined") return;

        try {
            const token = localStorage.getItem("access_token");
            const refresh = localStorage.getItem("refresh_token");
            const role = localStorage.getItem("role");
            const username = localStorage.getItem("username");

            if (token && refresh && role && username) {
                dispatch(
                    loginSuccess({
                        username,
                        role,
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
