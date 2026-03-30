import api from './api';

export const authService = {
    async getPlans() {
        const response = await api.get('/auth/plans');
        const plans = Array.isArray(response.data) ? response.data : [];
        return plans.map((plan) => ({
            ...plan,
            feature_list: Array.isArray(plan.feature_list) ? plan.feature_list : [],
        }));
    },

    async registerOrg(payload) {
        // payload: { organization: {...}, owner: {...}, plan_name: 'Pro' }
        const response = await api.post('/auth/register-org', payload);
        return response.data;
    },

    async login(credentials) {
        const response = await api.post('/auth/login', credentials);
        return response.data;
    }
};
