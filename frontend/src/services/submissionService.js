import api from '@/services/api';

export const submissionService = {
    // GET /api/submissions/project/<id> - List all work for a project
    async getProjectSubmissions(projectId) {
        const response = await api.get(`/submissions/project/${projectId}`);
        const payload = response.data?.data ?? response.data ?? {};
        return {
            submissions: Array.isArray(payload?.submissions) ? payload.submissions : [],
            total: Number(payload?.total ?? 0),
            page: Number(payload?.page ?? 1),
            pages: Number(payload?.pages ?? 1),
        };
    },

    // GET /api/submissions/stats/<id> - Aggregated analytics
    async getProjectStats(projectId) {
        const response = await api.get(`/submissions/stats/${projectId}`);
        return response.data;
    },

    // PATCH /api/submissions/review/<id> - Manual override of AI feedback
    async reviewSubmission(submissionId, data) {
        const response = await api.patch(`/submissions/review/${submissionId}`, data);
        return response.data;
    },

    // POST /api/submissions/evaluate/<id> - Trigger Gemini manually
    async triggerAIEvaluation(submissionId, force = false) {
        const url = force ? `/submissions/evaluate/${submissionId}?force=true` : `/submissions/evaluate/${submissionId}`;
        const response = await api.post(url);
        return response.data;
    },

    // GET /api/submissions/all - Consolidated list for professors
    async getAllProfessorSubmissions() {
        const response = await api.get('/submissions/all');
        const payload = response.data?.data ?? response.data ?? {};
        return {
            submissions: Array.isArray(payload?.submissions) ? payload.submissions : [],
            total: Number(payload?.total ?? 0),
            page: Number(payload?.page ?? 1),
            pages: Number(payload?.pages ?? 1),
        };
    },

    // SECURITY: Generate a short-lived signed download URL instead of passing JWT in query string.
    async getDownloadUrl(submissionId, inline = false) {
        const response = await api.get(`/submissions/${submissionId}/download-url`);
        let url = response.data.data.url;
        if (inline) url += '&inline=true';
        return url;
    }
};
