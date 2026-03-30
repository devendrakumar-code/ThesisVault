import {defineStore} from 'pinia';
import api from '@/services/api';

export const useAuthStore = defineStore('auth', {
    state: () => ({
        // SECURITY: Use sessionStorage instead of localStorage.
        // sessionStorage is cleared when the tab closes, reducing token exposure.
        user: JSON.parse(sessionStorage.getItem('user')) || null,
        token: sessionStorage.getItem('token') || null,
        loading: false,
        error: null,
    }),

    getters: {
        isAuthenticated: (state) => !!state.token,
        roles: (state) => (state.user?.roles || []).map(r => r.toLowerCase()),
        userRole: (state) => state.user?.roles?.[0] || null,
        orgId: (state) => state.user?.organization_id || null,
        isAdmin: (state) => (state.user?.roles || []).map(r => r.toLowerCase()).includes('admin'),
        isProfessor: (state) => (state.user?.roles || []).map(r => r.toLowerCase()).includes('professor'),
        isStudent: (state) => (state.user?.roles || []).map(r => r.toLowerCase()).includes('student'),
    },

    actions: {
        async login(email, password) {
            this.loading = true;
            this.error = null;
            try {
                const response = await api.post('/auth/login', {email, password});
                this.token = response.data.token;
                this.user = response.data.user;

                sessionStorage.setItem('token', this.token);
                sessionStorage.setItem('user', JSON.stringify(this.user));
                return true;
            } catch (err) {
                this.error = err.response?.data?.error || 'Login failed';
                throw err;
            } finally {
                this.loading = false;
            }
        },

        logout() {
            // Optional: call backend logout to revoke token
            api.post('/auth/logout').catch(() => {});

            this.user = null;
            this.token = null;
            sessionStorage.removeItem('token');
            sessionStorage.removeItem('user');
        }
    },
});
