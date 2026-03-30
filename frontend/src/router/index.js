import {createRouter, createWebHistory} from 'vue-router';
import {useAuthStore} from '@/stores/authStore';

const routes = [
    {
        path: '/',
        name: 'landing',
        component: () => import('@/views/LandingView.vue'),
        meta: {public: true}
    },
    {
        path: '/login',
        name: 'login',
        component: () => import('@/views/auth/LoginView.vue'),
        meta: {public: true}
    },
    {
        path: '/register-org',
        name: 'register-org',
        component: () => import('@/views/auth/RegisterOrgView.vue'),
        meta: {public: true}
    },
    {
        path: '/student-join',
        name: 'student-join',
        component: () => import('@/views/auth/StudentJoinView.vue'),
        meta: {public: true}
    },
    {
        path: '/accept-invite',
        name: 'accept-invite',
        component: () => import('@/views/auth/AcceptInviteView.vue'),
        meta: {public: true}
    },
    // The Dynamic Traffic Controller
    {
        path: '/dashboard',
        name: 'dashboard',
        meta: {requiresAuth: true},
        beforeEnter: (to, from, next) => {
            const authStore = useAuthStore();

            if (authStore.isAdmin) {
                next({name: 'admin-dashboard'});
            } else if (authStore.isProfessor) {
                next({name: 'professor-dashboard'});
            } else if (authStore.isStudent) {
                next({name: 'student-dashboard'});
            } else {
                next({name: 'login'});
            }
        }
    },
    // --- Admin Routes ---
    {
        path: '/admin',
        name: 'admin-dashboard',
        component: () => import('@/views/admin/AdminDashboardView.vue'),
        meta: {requiresAuth: true, role: 'admin'}
    },
    // --- Professor Routes ---
    {
        path: '/professor',
        name: 'professor-dashboard',
        component: () => import('@/views/professor/ProfessorDashboardView.vue'),
        meta: {requiresAuth: true, role: 'professor'}
    },
    {
        path: '/professor/students',
        name: 'professor-students',
        component: () => import('@/views/professor/ManagedStudentsView.vue'),
        meta: {requiresAuth: true, role: 'professor'}
    },
    {
        path: '/professor/submissions',
        name: 'professor-submissions',
        component: () => import('@/views/professor/AllSubmissionsView.vue'),
        meta: {requiresAuth: true, role: 'professor'}
    },
    {
        path: '/projects/:id',
        name: 'project-detail',
        component: () => import('@/views/professor/ProjectDetailView.vue'),
        meta: {requiresAuth: true, role: 'professor'}
    },
    // --- Student Routes ---
    {
        path: '/student',
        name: 'student-dashboard',
        component: () => import('@/views/student/StudentDashboardView.vue'),
        meta: {requiresAuth: true, role: 'student'}
    },
    {
        path: '/student/project/:id',
        name: 'student-workspace',
        component: () => import('@/views/student/ProjectWorkspaceView.vue'),
        meta: {requiresAuth: true, role: 'student'}
    },
    {
        path: '/student/submission/:id',
        name: 'student-submission-detail',
        component: () => import('@/views/student/SubmissionDetailView.vue'),
        meta: {requiresAuth: true, role: 'student'}
    },
    // --- Shared Routes ---
    {
        path: '/profile',
        name: 'profile-settings',
        component: () => import('@/views/profile/ProfileSettingsView.vue'),
        meta: {requiresAuth: true}
    },
    {
        path: '/subscription',
        name: 'subscription',
        component: () => import('@/views/admin/SubscriptionView.vue'),
        meta: {requiresAuth: true, role: 'admin'}
    }
];

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes
});

// Global Navigation Guard
router.beforeEach((to, from, next) => {
    const authStore = useAuthStore();
    const isAuthenticated = authStore.isAuthenticated;

    // 1. Handle Public Routes first (prevents unnecessary login redirects)
    if (to.meta.public) {
        // If already logged in, redirect landing/login to dashboard
        if (isAuthenticated && (to.name === 'login' || to.name === 'landing')) {
            return next({name: 'dashboard'});
        }
        return next();
    }

    // 2. Handle Protected Routes
    if (to.meta.requiresAuth && !isAuthenticated) {
        return next({name: 'login'});
    }

    // 3. Role-Based Access Control
    if (to.meta.role && !authStore.roles.includes(to.meta.role)) {
        return next({name: 'dashboard'});
    }

    next();
});

export default router;
