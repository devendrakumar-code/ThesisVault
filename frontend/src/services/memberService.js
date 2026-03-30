import api from '@/services/api';

export const memberService = {
    /**
     * Students register themselves using a Project's unique join_code.
     * Logic matches backend/routes/members.py -> student_join [cite: 46]
     */
    async studentJoin(payload) {
        // payload: { join_code, email, password, name, major, semester }
        const response = await api.post('/members/student-join', payload);
        return response.data;
    },

    async joinProject(payload) {
        const response = await api.post('/members/join-project', payload);
        return response.data;
    },

    /**
     * Admin invites a professor.
     * Logic matches backend/routes/members.py -> invite_professor [cite: 42]
     */
    async inviteProfessor(payload) {
        const response = await api.post('/members/invite-professor', payload);
        return response.data;
    },

    /**
     * Fetch invitation details using a token (Public)
     */
    async getInviteDetails(token) {
        const response = await api.get(`/members/invite-details?token=${token}`);
        return response.data;
    },

    /**
     * Submit onboarding for an invited professor (Public)
     */
    async acceptInvite(payload) {
        const response = await api.post('/members/accept-invite', payload);
        return response.data;
    }
};
