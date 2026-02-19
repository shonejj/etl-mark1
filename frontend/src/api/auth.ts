import { useNavigate } from "react-router-dom";
import api from "./client";
import { useAuthStore } from "../context/authStore";

export const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    useAuthStore.getState().login(data.user, data.access_token, data.refresh_token);
    return data.user;
};

export const logout = async () => {
    try {
        await api.post("/auth/logout");
    } finally {
        useAuthStore.getState().logout();
    }
};

export const getMe = async () => {
    const { data } = await api.get("/auth/me");
    useAuthStore.getState().setUser(data);
    return data;
};
