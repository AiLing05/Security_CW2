import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { apiFetch } from "../lib/apiFetch";
import { setSessionUser } from "../lib/browserSession";

export const loginUser = createAsyncThunk("user/loginUser", async ({ username, password }, { rejectWithValue }) => {
  try {
    const login = await apiFetch("/api/token/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }) });
    if (!login.ok) throw new Error("Invalid credentials");
    const response = await apiFetch("/api/me/");
    if (!response.ok) throw new Error("Could not load your account.");
    const user = await response.json();
    setSessionUser(user);
    return user;
  } catch (error) { return rejectWithValue(error.message); }
});

const userSlice = createSlice({
  name: "user",
  initialState: { user: null, loading: false, error: null },
  reducers: {
    logout: (state) => { state.user = null; state.loading = false; state.error = null; },
    loginSuccess: (state, action) => { state.user = action.payload; state.loading = false; state.error = null; },
  },
  extraReducers: (builder) => {
    builder.addCase(loginUser.pending, (state) => { state.loading = true; state.error = null; })
      .addCase(loginUser.fulfilled, (state, action) => { state.user = action.payload; state.loading = false; })
      .addCase(loginUser.rejected, (state, action) => { state.loading = false; state.error = action.payload; });
  },
});
export const { logout, loginSuccess } = userSlice.actions;
export default userSlice.reducer;
