<template>
  <aside class="w-64 glass-panel min-h-[calc(100vh-5rem)] rounded-xl my-4 ml-4 hidden md:block overflow-hidden shadow-sm transition-all duration-300">
    <div class="h-full flex flex-col">
      <div class="flex-1 py-6 space-y-2 px-4 overflow-y-auto">
        <router-link 
          to="/dashboard" 
          class="flex items-center px-4 py-3 text-sm font-semibold rounded-xl transition-all duration-200"
          :class="isActive('/dashboard') ? 'bg-gradient-to-r from-indigo-500/10 to-blue-500/10 text-indigo-700 shadow-sm border border-indigo-100/50' : 'text-slate-600 hover:bg-slate-100 hover:text-indigo-600'"
        >
          <span class="mr-3 text-xl transition-transform duration-200 group-hover:scale-110">📊</span>
          Dashboard
        </router-link>

        <template v-if="authStore.isAdmin">
          <div class="pt-6 pb-2 px-3 text-xs font-bold text-slate-400 uppercase tracking-widest">
            Administration
          </div>
          <router-link 
            to="/admin" 
            class="flex items-center px-4 py-3 text-sm font-semibold rounded-xl transition-all duration-200 text-slate-600 hover:bg-slate-100 hover:text-indigo-600"
          >
            <span class="mr-3 text-xl transition-transform duration-200 group-hover:scale-110">🏢</span>
            Manage Institution
          </router-link>
        </template>

        <template v-if="authStore.isProfessor">
          <div class="pt-6 pb-2 px-3 text-xs font-bold text-slate-400 uppercase tracking-widest">
            Teaching
          </div>
          <router-link 
            to="/professor" 
            class="flex items-center px-4 py-3 text-sm font-semibold rounded-xl transition-all duration-200"
            :class="isActive('/professor') && !isActive('/professor/students') ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'text-slate-600 hover:bg-slate-100 hover:text-indigo-600'"
          >
            <span class="mr-3 text-xl transition-transform duration-200 group-hover:scale-110">📚</span>
            My Projects
          </router-link>
          <router-link 
            to="/professor/students" 
            class="flex items-center px-4 py-3 text-sm font-semibold rounded-xl transition-all duration-200"
            :class="isActive('/professor/students') ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'text-slate-600 hover:bg-slate-100 hover:text-indigo-600'"
          >
            <span class="mr-3 text-xl transition-transform duration-200 group-hover:scale-110">👨‍🎓</span>
            Managed Students
          </router-link>
          <router-link 
            to="/professor/submissions" 
            class="flex items-center px-4 py-3 text-sm font-semibold rounded-xl transition-all duration-200"
            :class="isActive('/professor/submissions') ? 'bg-indigo-50 text-indigo-700 border border-indigo-100' : 'text-slate-600 hover:bg-slate-100 hover:text-indigo-600'"
          >
            <span class="mr-3 text-xl transition-transform duration-200 group-hover:scale-110">📁</span>
            All Submissions
          </router-link>
        </template>

        <template v-if="authStore.isStudent">
          <div class="pt-6 pb-2 px-3 text-xs font-bold text-slate-400 uppercase tracking-widest">
            Learning
          </div>
          <router-link 
            to="/student" 
            class="flex items-center px-4 py-3 text-sm font-semibold rounded-xl transition-all duration-200 text-slate-600 hover:bg-slate-100 hover:text-indigo-600"
          >
            <span class="mr-3 text-xl transition-transform duration-200 group-hover:scale-110">🎓</span>
            Joined Projects
          </router-link>
        </template>

        <div class="pt-6 pb-2 px-3 text-xs font-bold text-slate-400 uppercase tracking-widest">
          Account
        </div>
        <router-link 
          to="/profile" 
          class="flex items-center px-4 py-3 text-sm font-semibold rounded-xl transition-all duration-200"
          :class="isActive('/profile') ? 'bg-gradient-to-r from-indigo-500/10 to-blue-500/10 text-indigo-700 shadow-sm border border-indigo-100/50' : 'text-slate-600 hover:bg-slate-100 hover:text-indigo-600'"
        >
          <span class="mr-3 text-xl transition-transform duration-200 group-hover:scale-110">👤</span>
          Profile Settings
        </router-link>
      </div>

      <div class="p-4 border-t border-slate-200/50 bg-slate-50/50 text-center">
        <p class="text-xs font-medium text-slate-400">ThesisVault v0.1.0</p>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { useAuthStore } from '@/stores/authStore';
import { useRoute } from 'vue-router';

const authStore = useAuthStore();
const route = useRoute();

const isActive = (path) => route.path.startsWith(path);
</script>
