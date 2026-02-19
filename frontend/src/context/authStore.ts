import { create } from 'zustand';

interface User {
    id: number;
    email: string;
    full_name: string;
    role: string;
    avatar_url?: string;
}

interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (user: User, token: string, refreshToken?: string) => void;
    logout: () => void;
    setUser: (user: User) => void;
    setLoading: (isLoading: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
    user: null,
    isAuthenticated: !!localStorage.getItem('token'),
    isLoading: true, // Start loading to check session on mount

    login: (user, token, refreshToken) => {
        localStorage.setItem('token', token);
        if (refreshToken) localStorage.setItem('refresh_token', refreshToken);
        set({ user, isAuthenticated: true });
    },

    logout: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        set({ user: null, isAuthenticated: false });
    },

    setUser: (user) => set({ user, isLoading: false }),
    setLoading: (isLoading) => set({ isLoading }),
}));
