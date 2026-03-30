import api from '@/services/api';

export const planService = {
    async getAvailablePlans() {
        // This hits a public endpoint to show plans before registration
        const response = await api.get('/auth/plans');
        return response.data; // Expected: { success: true, data: [{name: 'Free', ...}, {name: 'Pro', ...}] }
    }
};
