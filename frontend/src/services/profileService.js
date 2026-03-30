import api from '@/services/api';

export const profileService = {
    // GET /api/profiles/me - Fetches user data + role-specific details
    async getMyProfile() {
        const response = await api.get('/profiles/me');
        return response.data; // Returns { success, message, data }
    },

    // PATCH /api/profiles/me - Updates name, department, or major/semester
    async updateProfile(payload) {
        const response = await api.post('/profiles/me', payload); // Backend uses PATCH or POST depending on routing
        return response.data;
    }
};
