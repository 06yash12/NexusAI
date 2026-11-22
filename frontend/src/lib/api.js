import axios from "axios";

// Using relative "/api" leverages the Vite proxy to http://127.0.0.1:8000,
// completely eliminating Windows localhost IPv4/IPv6 (::1) net::ERR_CONNECTION_REFUSED issues!
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api"
});

export const getError = (error) => error?.response?.data?.detail || error.message || "Unexpected error";
