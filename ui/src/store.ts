import { configureStore } from "@reduxjs/toolkit";
import { mlmbApi } from "./services/mlmb";

export const store = configureStore({
  reducer: {
    [mlmbApi.reducerPath]: mlmbApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(mlmbApi.middleware),
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
// Inferred type: {posts: PostsState, comments: CommentsState, users: UsersState}
export type AppDispatch = typeof store.dispatch;
