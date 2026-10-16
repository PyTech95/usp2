import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@/index.css";
import "@/styles/home-reference.css";
import "@/styles/craft-reference.css";
import "@/styles/workshops-reference.css";
import "@/styles/rakhigarhi-reference.css";
import "@/styles/theatre-reference.css";
import "@/styles/about-reference.css";
import "@/styles/live-editor-access.css";
import App from "@/App";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
