import api from '@/services/api';

export const adminService = {
    // POST /api/members/invite-professor - Admin only 
    // POST /api/members/invite-professor - Admin only 
    async inviteProfessor(payload) {
        const response = await api.post('/members/invite-professor', payload);
        return response.data;
    },

    // GET /api/members?role=... - List all members in org
    async getMembers(role = null) {
        const url = role ? `/members/?role=${role}` : '/members/';
        const response = await api.get(url);
        return Array.isArray(response.data?.members) ? response.data.members : [];
    },

    // PATCH /api/members/:id/status - Toggle active status
    async toggleUserStatus(userId) {
        const response = await api.patch(`/members/${userId}/status`);
        return response.data;
    },

    // GET /api/projects/ - List all projects in org
    async getProjects() {
        const response = await api.get('/projects/');
        return Array.isArray(response.data?.data) ? response.data.data : [];
    },

    // PATCH /api/projects/:id/status - Toggle project status
    async toggleProjectStatus(projectId, status) {
        const response = await api.patch(`/projects/${projectId}/status`, { status });
        return response.data;
    },

    async getSubscriptionSummary() {
        const response = await api.get('/auth/subscription-summary');
        return response.data;
    },

    async getAvailablePlans() {
        const response = await api.get('/auth/plans');
        return Array.isArray(response.data) ? response.data : [];
    },

    async changePlan(planName) {
        const response = await api.post('/auth/change-plan', { plan_name: planName });
        return response.data;
    }
};
