import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import {
  PredictionRequest,
  PredictionResponse,
  RankingsResponse,
} from "./types";

// API base URL - uses environment variable in production, localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:7071";

// Define a service using a base URL and expected endpoints
export const mlmbApi = createApi({
  reducerPath: "mlmb",
  baseQuery: fetchBaseQuery({
    baseUrl: API_BASE_URL,
  }),
  endpoints: (builder) => ({
    getRankings: builder.query<RankingsResponse, "men" | "women">({
      query: (gender) => `rankings/${gender}`,
    }),
    predict: builder.mutation<PredictionResponse, PredictionRequest>({
      query: (data) => ({
        url: "/predictions",
        method: "POST",
        body: data,
      }),
    }),
  }),
});

// Export hooks for usage in functional components, which are
// auto-generated based on the defined endpoints
export const { useGetRankingsQuery, usePredictMutation } = mlmbApi;
