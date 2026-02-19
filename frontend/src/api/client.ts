import axios from "axios";

// Base API instance
const api = axios.create({
    baseURL: "http://localhost:8000/api",
    headers: {
        "Content-Type": "application/json",
    },
});

// Request interceptor for auth token
api.interceptors.request.use((config) => {
    const token = localStorage.getItem("token");
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        // Handle 401 Unauthorized (token expiry)
        if (error.response?.status === 401 && !error.config._retry) {
            error.config._retry = true;
            try {
                const refreshToken = localStorage.getItem("refresh_token");
                if (refreshToken) {
                    const { data } = await axios.post("/api/auth/refresh", { refresh_token: refreshToken });
                    localStorage.setItem("token", data.access_token);
                    if (data.refresh_token) {
                        localStorage.setItem("refresh_token", data.refresh_token);
                    }
                    api.defaults.headers.common["Authorization"] = `Bearer ${data.access_token}`;
                    return api(error.config);
                }
            } catch (refreshError) {
                // Logout if refresh fails
                localStorage.removeItem("token");
                localStorage.removeItem("refresh_token");
                window.location.href = "/login";
            }
        }
        return Promise.reject(error);
    }
);

export default api;
