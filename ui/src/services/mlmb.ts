import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import {
  PredictionRequest,
  PredictionResponse,
  PredictionsListResponse,
  PredictionsHistoryQuery,
  RankingsResponse,
  Sport,
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
    getRankings: builder.query<RankingsResponse, Sport>({
      query: (sport) => `rankings/${sport}`,
    }),
    predict: builder.mutation<PredictionResponse, PredictionRequest>({
      query: (data) => ({
        url: "/predictions",
        method: "POST",
        body: data,
      }),
    }),
    getPrediction: builder.query<
      PredictionResponse,
      { prediction_id: string; sport: Sport }
    >({
      query: ({ prediction_id, sport }) =>
        `predictions/${prediction_id}?sport=${sport}`,
    }),
    getPredictionsHistory: builder.query<
      PredictionsListResponse,
      PredictionsHistoryQuery
    >({
      query: (params) => {
        const searchParams = new URLSearchParams();
        searchParams.set("sport", params.sport);
        if (params.home_team) searchParams.set("home_team", params.home_team);
        if (params.away_team) searchParams.set("away_team", params.away_team);
        if (params.model_version)
          searchParams.set("model_version", params.model_version);
        if (params.start_date)
          searchParams.set("start_date", params.start_date);
        if (params.end_date) searchParams.set("end_date", params.end_date);
        if (params.limit) searchParams.set("limit", params.limit.toString());
        if (params.before_id) searchParams.set("before_id", params.before_id);
        if (params.after_id) searchParams.set("after_id", params.after_id);
        return `predictions?${searchParams.toString()}`;
      },
    }),
  }),
});

// Export hooks for usage in functional components, which are
// auto-generated based on the defined endpoints
export const {
  useGetRankingsQuery,
  usePredictMutation,
  useGetPredictionQuery,
  useGetPredictionsHistoryQuery,
} = mlmbApi;
