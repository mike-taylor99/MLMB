import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { MatchupInput, MatchupOutput } from "./types";

// Define a service using a base URL and expected endpoints
// Uses /api for Azure Static Web Apps Functions (hosted together with frontend)
export const mlmbApi = createApi({
  reducerPath: "mlmb",
  baseQuery: fetchBaseQuery({
    baseUrl: "/api",
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
