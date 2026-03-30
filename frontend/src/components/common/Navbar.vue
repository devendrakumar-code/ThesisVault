<template>
  <nav class="sticky top-0 z-50 transition-all duration-300 px-4 pt-2">
    <div class="glass-navbar rounded-2xl shadow-lg border border-white/20 backdrop-blur-xl bg-white/70 overflow-hidden">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16 items-center">
          
          <!-- BRAND & PRIMARY NAV -->
          <div class="flex items-center gap-8">
            <router-link to="/dashboard" class="flex items-center gap-3 group transition-all duration-300">
              <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-blue-600 shadow-indigo-200 shadow-lg flex items-center justify-center transform group-hover:scale-110 group-hover:rotate-6 transition-all duration-300">
                <i class="fas fa-feather-pointed text-white text-lg"></i>
              </div>
              <span class="text-xl font-black text-slate-900 tracking-tight">Thesis<span class="text-indigo-600">Vault</span></span>
            </router-link>

            <!-- Role-Specific Links (Requirement: Contextual Navigation) -->
            <!-- Links removed as requested -->
          </div>

          <!-- RIGHT ACTIONS -->
          <div class="flex items-center gap-4">
            
            <!-- Plan Badge (SaaS Requirement: Plan Transparency) -->
            <button 
                  @click="handleLogout"
                  class="hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-50 text-slate-600 hover:bg-rose-50 hover:text-rose-600 text-xs font-bold transition-all duration-300 border border-slate-100"
                >
                  <i class="fas fa-right-from-bracket opacity-70"></i>
                  Sign Out
            </button>

            <!-- User Menu Dropdown -->
            <div class="relative group">
              <button class="flex items-center gap-3 p-1 rounded-2xl hover:bg-slate-100/50 transition-all duration-300 group">
                <div class="text-right hidden sm:block mr-1">
                  <p class="text-xs font-black text-slate-900 leading-none mb-1">{{ authStore.user?.name }}</p>
                  <p class="text-[10px] font-bold text-indigo-500 uppercase tracking-tighter">{{ authStore.userRole }}</p>
                </div>
                <div class="w-10 h-10 rounded-xl bg-indigo-50 border-2 border-white shadow-sm overflow-hidden transform group-hover:scale-105 transition-transform duration-300">
                  <img v-if="authStore.user?.profile_image" :src="getFullImageUrl(authStore.user.profile_image)" class="w-full h-full object-cover" />
                  <div v-else class="w-full h-full flex items-center justify-center bg-indigo-100 text-indigo-600 font-black text-sm">
                    {{ authStore.user?.name?.charAt(0).toUpperCase() }}
                  </div>
                </div>
              </button>

              <!-- Dropdown Menu -->
              <div class="absolute right-0 mt-2 w-56 opacity-0 translate-y-2 pointer-events-none group-hover:opacity-100 group-hover:translate-y-0 group-hover:pointer-events-auto transition-all duration-300">
                <div class="p-2 bg-white rounded-2xl shadow-xl border border-slate-100 mt-1">
                  <div class="p-3 mb-2 border-b border-slate-50 lg:hidden">
                    <p class="text-xs font-black text-slate-400 uppercase tracking-widest">{{ planName }} Plan</p>
                  </div>
                  <router-link to="/profile" class="flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-bold text-slate-600 hover:bg-slate-50 hover:text-indigo-600 transition-all duration-200">
                    <i class="fas fa-id-card-clip opacity-50"></i> Profile Settings
                  </router-link>
                  <router-link v-if="authStore.isAdmin" to="/subscription" class="flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-bold text-slate-600 hover:bg-indigo-50 hover:text-indigo-600 transition-all duration-200">
                    <i class="fas fa-receipt opacity-50"></i> Subscription History
                  </router-link>
                  <div class="h-px bg-slate-50 my-1"></div>
                  <button @click="handleLogout" class="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-bold text-rose-600 hover:bg-rose-50 transition-all duration-200 text-left">
                    <i class="fas fa-right-from-bracket opacity-50"></i> Sign Out
                  </button>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue';
import { useAuthStore } from '@/stores/authStore';
import { useRouter } from 'vue-router';

const authStore = useAuthStore();
const router = useRouter();

const planName = computed(() => authStore.user?.organization?.plan?.name || null);

const professorLinks = [
  { to: '/professor', label: 'Dashboard' },
  { to: '/professor/students', label: 'Students' },
  { to: '/professor/submissions', label: 'Submissions' },
];

const studentLinks = [
  { to: '/student', label: 'My Workspace' },
];

const getFullImageUrl = (path) => {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
  const normalizedPath = path.startsWith('/') ? path.slice(1) : path;
  return `${baseUrl}/${normalizedPath}`;
};

const handleLogout = () => {
  authStore.logout();
  router.push('/login');
};
</script>
