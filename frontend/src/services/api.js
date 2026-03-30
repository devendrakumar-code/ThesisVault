import axios from 'axios';
import {useAuthStore} from '@/stores/authStore';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5000/api',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor to add JWT to headers
api.interceptors.request.use((config) => {
    const authStore = useAuthStore();
    if (authStore.token) {
        // Matches SECURITY_TOKEN_AUTHENTICATION_HEADER in your config.py
        config.headers.Authorization = authStore.token;
    }
    return config;
});

// Interceptor to handle global errors (like expired tokens)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401 && !error.config?.url?.includes('/auth/logout')) {
            const authStore = useAuthStore();
            authStore.logout(); // Wipe state if token is invalid
        }
        
        // --- SaaS "Plan Awareness" (Requirement: Frontend-only restriction is not acceptable) ---
        if (error.response?.status === 403) {
            const msg = error.response.data?.message || "";
            if (msg.toLowerCase().includes("subscription") || msg.toLowerCase().includes("limit") || msg.toLowerCase().includes("upgrade")) {
                error.isSubscriptionError = true;
                // Here you could also trigger a global event or store state
            }
        }

        return Promise.reject(error);
    }
);

export default api;
