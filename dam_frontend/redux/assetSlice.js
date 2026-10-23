import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";


export const fetchAssets = createAsyncThunk("assets/fetchAssets", async (_, thunkAPI) => {
  try {
    const token = localStorage.getItem("access_token");


    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/assets/`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Fetch failed (${res.status}): ${errorText}`);
    }

    const data = await res.json();
    return data;
  } catch (err) {
    return thunkAPI.rejectWithValue(err.message);
  }
});

const assetSlice = createSlice({
  name: "assets",
  initialState: {
    items: [],
    loading: false,
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchAssets.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAssets.fulfilled, (state, action) => {
        state.loading = false;


        if (action.payload?.results) {
          state.items = action.payload.results;
        } else if (Array.isArray(action.payload)) {
          state.items = action.payload;
        } else {
          state.items = [];
        }

        state.error = null;
      })
      .addCase(fetchAssets.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || "Failed to load assets";
      });
  },
});

export default assetSlice.reducer;
