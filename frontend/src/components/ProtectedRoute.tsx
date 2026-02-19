import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../context/authStore";

export const ProtectedRoute = () => {
    const { isAuthenticated } = useAuthStore();
    if (!isAuthenticated) return <Navigate to="/login" replace />;
    return <Outlet />;
};

export const PublicRoute = () => {
    const { isAuthenticated } = useAuthStore();
    if (isAuthenticated) return <Navigate to="/" replace />;
    return <Outlet />;
};
