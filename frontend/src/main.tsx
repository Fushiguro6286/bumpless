import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import "./index.css";
import Layout from "./components/Layout";
import NewMigration from "./pages/NewMigration";
import Benchmark from "./pages/Benchmark";
import Placeholder from "./pages/Placeholder";
import Recipes from "./pages/Recipes";
import Run from "./pages/Run";
import Runs from "./pages/Runs";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <NewMigration /> },
      { path: "runs", element: <Runs /> },
      { path: "runs/:id", element: <Run /> },
      { path: "recipes", element: <Recipes /> },
      { path: "radar", element: <Placeholder title="Upgrade Radar" note="Coming in a later build step." /> },
      { path: "benchmark", element: <Benchmark /> },
      { path: "status", element: <Placeholder title="Status" note="Coming in a later build step." /> },
      { path: "*", element: <Placeholder title="Not found" note="This page does not exist." /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(<StrictMode><RouterProvider router={router} /></StrictMode>);
