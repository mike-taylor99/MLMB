import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Error } from "./components/Error";
import { Home } from "./components/Home";
import { TeamList } from "./components/TeamList";
import { Prediction } from "./components/Prediction";

let router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    errorElement: <Error />,
    children: [
      {
        // errorElement: <Error />,
        children: [
          {
            index: true,
            element: <Home />,
          },
          {
            path: "predict",
            element: <Prediction />,
          },
          {
            path: "teams",
            element: <TeamList />,
          },
        ],
      },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} fallbackElement={<p>Loading...</p>} />;
}

if (import.meta.hot) {
  import.meta.hot.dispose(() => router.dispose());
}
