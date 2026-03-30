import api from './api';

export const adminService = {
    /**
     * Fetch all available subscription plans.
     */
    async getAvailablePlans() {
        const response = await api.get('/admin/plans');
        return response.data.data;
    },

    // Alias for backward compatibility if needed
    async getPlans() { return this.getAvailablePlans(); },

    /**
     * Fetch the organization's subscription history and activity logs.
     */
    async getHistory() {
        const response = await api.get('/admin/organizations/me/history');
        return response.data.data;
    },

    /**
     * Fetch a consolidated summary of the current organization and plan.
     */
    async getSubscriptionSummary() {
        const response = await api.get('/admin/organizations/me');
        return response.data.data;
    },

    /**
     * Platform Management: Fetch members (students/professors).
     */
    async getMembers(role = null) {
        const url = role ? `/admin/members?role=${role}` : '/admin/members';
        const response = await api.get(url);
        return response.data.data;
    },

    /**
     * Platform Management: Fetch all projects.
     */
    async getProjects() {
        const response = await api.get('/admin/projects');
        return response.data.data;
    },

    /**
     * Platform Management: Toggle user active status.
     */
    async toggleUserStatus(userId) {
        const response = await api.post(`/admin/users/${userId}/toggle`);
        return response.data;
    },

    /**
     * Platform Management: Toggle project status (active/suspended).
     */
    async toggleProjectStatus(projectId) {
        const response = await api.post(`/admin/projects/${projectId}/toggle`);
        return response.data;
    },

    /**
     * Platform Management: Invite a new professor.
     * Proxies to member service logic.
     */
    async inviteProfessor(payload) {
        const response = await api.post('/members/invite-professor', payload);
        return response.data;
    },

    /**
     * Upgrade/Change the user's organization plan.
     */
    async changePlan(planName) {
        const response = await api.post('/admin/organizations/me/upgrade', { plan_name: planName });
        return response.data;
    },

    // Alias for transition
    async upgradePlan(planName) { return this.changePlan(planName); },

    /**
     * Suspend the current organization.
     */
    async suspendOrg() {
        const response = await api.post('/admin/organizations/me/suspend');
        return response.data;
    },

    /**
     * Resume the current organization.
     */
    async resumeOrg() {
        const response = await api.post('/admin/organizations/me/resume');
        return response.data;
    }
};
