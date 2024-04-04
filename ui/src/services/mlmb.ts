import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { MatchupInput, MatchupOutput } from "./types";

// Define a service using a base URL and expected endpoints
export const mlmbApi = createApi({
  reducerPath: "mlmb",
  baseQuery: fetchBaseQuery({
    baseUrl: "https://mlmb-api.azurewebsites.net/",
    credentials: "same-origin",
    mode: "cors",
  }),
  endpoints: (builder) => ({
    getTop25: builder.query<{ [name: string]: number }, "men" | "women">({
      query: (arg) => `top-25/${arg}`,
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
