import api from '@/services/api';

export const projectService = {
    async getMyProjects() {
        const response = await api.get('/projects/');
        const payload = response.data;
        if (Array.isArray(payload)) return payload;
        if (Array.isArray(payload?.data)) return payload.data;
        return [];
    },

    async createProject(projectPayload) {
        const formData = new FormData();
        formData.append('name', projectPayload.name?.trim() || '');
        formData.append('description', projectPayload.description?.trim() || '');
        formData.append('milestones', JSON.stringify(projectPayload.milestones || []));
        if (projectPayload.problemStatementFile) {
            formData.append('problem_statement_file', projectPayload.problemStatementFile);
        }

        const response = await api.post('/projects/', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        });
        return response.data?.data ?? response.data;
    },

    async getProjectDetails(projectId) {
        const response = await api.get(`/projects/${projectId}`);
        return response.data;
    },
    async updateProjectStatus(projectId, status) {
        const response = await api.patch(`/projects/${projectId}/status`, { status });
        return response.data?.data ?? response.data;
    },
    async regenerateJoinCode(projectId) {
        const response = await api.post(`/projects/${projectId}/regenerate-code`);
        return response.data;
    },

    async getProjectRoster(projectId) {
        const response = await api.get(`/projects/${projectId}/students`);
        const payload = response.data;
        if (Array.isArray(payload)) return payload;
        if (Array.isArray(payload?.data)) return payload.data;
        return [];
    },

    async removeStudent(projectId, studentId) {
        const response = await api.delete(`/projects/${projectId}/students/${studentId}`);
        return response.data;
    },

    async getGlobalRoster() {
        const response = await api.get('/projects/students/all');
        const payload = response.data;
        if (Array.isArray(payload)) return payload;
        if (Array.isArray(payload?.data)) return payload.data;
        return [];
    }
};


