import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { MatchupInput, MatchupOutput } from "./types";

// API base URL - uses environment variable in production, localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:7071";

// Define a service using a base URL and expected endpoints
export const mlmbApi = createApi({
  reducerPath: "mlmb",
  baseQuery: fetchBaseQuery({
    baseUrl: API_BASE_URL,
  }),
  endpoints: (builder) => ({
    getTop25: builder.query<{ [name: string]: number }, "men" | "women">({
      query: (arg) => `top25/${arg}`,
    }),
    predict: builder.mutation<MatchupOutput[], MatchupInput[]>({
      query: (data) => ({
        url: "/predict",
        method: "POST",
        body: data,
      }),
    }),
  }),
});

// Export hooks for usage in functional components, which are
// auto-generated based on the defined endpoints
export const { useGetTop25Query, usePredictMutation } = mlmbApi;
