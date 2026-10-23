
import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";


export const loginUser = createAsyncThunk(
  "user/loginUser",
  async ({ username, password }, { rejectWithValue }) => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/token/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Invalid credentials");
      }

      const data = await res.json();
      const userPayload = {
        access: data.access,
        refresh: data.refresh,
        username,
        role: data.role || "user",
      };


      if (typeof window !== "undefined") {
        localStorage.setItem("user", JSON.stringify(userPayload));
        localStorage.setItem("access_token", data.access || "");
        localStorage.setItem("refresh_token", data.refresh || "");
        localStorage.setItem("role", userPayload.role);
        localStorage.setItem("username", username);
      }

      return userPayload;
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);


const getPersistedUser = () => {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem("user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const persisted = getPersistedUser();


const userSlice = createSlice({
  name: "user",
  initialState: {
    user: persisted || null,
    loading: false,
    error: null,
  },
  reducers: {
    logout: (state) => {
      state.user = null;
      state.loading = false;
      state.error = null;
      if (typeof window !== "undefined") {
        localStorage.clear();
      }
    },
    loginSuccess: (state, action) => {
      state.user = action.payload;
      state.loading = false;
      state.error = null;
      if (typeof window !== "undefined") {
        localStorage.setItem("user", JSON.stringify(action.payload));
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.user = action.payload;
        state.loading = false;
        state.error = null;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export const { logout, loginSuccess } = userSlice.actions;
export default userSlice.reducer;
