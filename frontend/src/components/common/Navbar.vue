<template>
  <nav class="glass-panel sticky top-0 z-50 rounded-b-xl mb-1 mt-0 mx-2 lg:mx-4 border-t-0 shadow-sm transition-all duration-300">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-16">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 shadow-md flex items-center justify-center transform hover:rotate-12 transition-transform duration-300">
            <span class="text-white font-bold text-lg">T</span>
          </div>
          <span class="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-700 to-blue-600 tracking-tight">ThesisVault</span>
        </div>
        <div class="flex items-center space-x-6">
          <div class="text-right hidden sm:block">
            <p class="text-sm font-bold text-slate-800">{{ authStore.user?.name }}</p>
            <p class="text-xs font-semibold tracking-wider text-indigo-500 uppercase">{{ authStore.userRole }}</p>
          </div>
          <button @click="handleLogout" class="px-4 py-2 rounded-lg text-sm font-semibold text-slate-600 hover:text-indigo-600 hover:bg-slate-100 transition-all duration-200">
            Logout
          </button>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useAuthStore } from '@/stores/authStore';
import { useRouter } from 'vue-router';

const authStore = useAuthStore();
const router = useRouter();

const handleLogout = () => {
  authStore.logout();
  router.push('/login');
};
</script>
