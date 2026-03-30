<template>
  <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
    <div class="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4 animate-fade-in">
      <div>
        <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">Student Dashboard</h1>
        <p class="text-slate-500 mt-1 font-medium">Manage your joined projects and academic progress.</p>
      </div>
    </div>

    <div class="glass-panel p-8 mb-10 text-white bg-gradient-to-r from-indigo-600 to-blue-600 rounded-2xl shadow-neon relative overflow-hidden animate-slide-up">
      <div class="absolute top-[-50%] right-[-10%] w-64 h-64 bg-white opacity-10 rounded-full mix-blend-overlay"></div>
      <div class="relative z-10">
        <h2 class="text-2xl font-bold mb-2">Join a New Project</h2>
        <p class="text-indigo-100 mb-6 font-medium">Enter the 8-character access code provided by your professor.</p>
        <form @submit.prevent="handleJoin" class="flex flex-col sm:flex-row gap-4 max-w-lg">
          <input
            v-model="joinCode"
            type="text"
            placeholder="e.g. ABC123XY"
            maxlength="8"
            class="flex-1 px-5 py-3 rounded-xl text-slate-900 bg-white/95 border-0 focus:ring-4 focus:ring-indigo-300 uppercase font-mono tracking-widest shadow-inner placeholder:text-slate-400 placeholder:normal-case transition-all"
          />
          <button type="submit" :disabled="joining" class="px-8 py-3 bg-white text-indigo-700 font-bold rounded-xl hover:bg-indigo-50 hover:scale-105 active:scale-95 transition-all shadow-md disabled:opacity-50 disabled:hover:scale-100 flex items-center justify-center gap-2">
            <span v-if="joining" class="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></span>
            {{ joining ? 'Joining...' : 'Join Project' }}
          </button>
        </form>
      </div>
    </div>

    <div class="mb-6 flex items-center justify-between animate-fade-in animation-delay-200">
      <h3 class="text-xl font-bold text-slate-900 border-l-4 border-indigo-500 pl-3">Your Projects</h3>
    </div>

    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="i in 3" :key="i" class="glass-card h-40 rounded-2xl animate-pulse bg-white/50">
        <div class="h-6 bg-slate-200 rounded w-3/4 mx-5 mt-6 mb-4"></div>
        <div class="h-4 bg-slate-200 rounded w-1/2 mx-5 mb-8"></div>
        <div class="h-10 bg-slate-100 rounded-xl mx-5"></div>
      </div>
    </div>

    <div v-else-if="projects.length === 0" class="text-center py-16 text-slate-500 bg-white/50 backdrop-blur-sm rounded-2xl border-2 border-dashed border-slate-300 animate-slide-up">
      <div class="text-5xl mb-4">PJ</div>
      <p class="font-medium text-lg text-slate-600">You haven't joined any projects yet.</p>
    </div>

    <div v-else class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="project in projects" :key="project.id" class="glass-card rounded-2xl p-6 flex flex-col justify-between group animate-fade-in">
        <div>
          <div class="flex items-start justify-between gap-3 mb-4">
            <div class="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center text-xl group-hover:bg-indigo-600 group-hover:text-white transition-colors duration-300 shadow-sm">
              PR
            </div>
            <span class="px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border"
              :class="project.status === 'completed' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : project.status === 'archived' ? 'bg-slate-100 text-slate-600 border-slate-200' : 'bg-indigo-50 text-indigo-700 border-indigo-200'">
              {{ project.status || 'active' }}
            </span>
          </div>
          <h4 class="text-xl font-bold text-slate-900 truncate mb-1" :title="project.name">{{ project.name }}</h4>
          <p class="text-sm font-medium text-slate-500 mb-4 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-blue-400"></span>
            Professor ID: {{ project.professor_id }}
          </p>
          <div class="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 mb-6">
            <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Project Outcome</p>
            <p v-if="project.status === 'completed'" class="text-sm font-bold text-emerald-700">Project completed and closed by professor</p>
            <p v-else-if="project.status === 'archived'" class="text-sm font-bold text-slate-700">Project archived and no longer active</p>
            <p v-else class="text-sm font-bold text-indigo-700">Project in progress</p>
            <p class="text-xs text-slate-500 mt-1">
              {{ project.student_grade ? `Your score: ${project.student_grade}` : 'Score not published yet' }}
            </p>
          </div>
        </div>
        <router-link
          :to="`/student/project/${project.id}`"
          class="w-full py-3 px-4 bg-slate-50 text-indigo-700 font-bold text-center rounded-xl hover:bg-indigo-600 hover:text-white transition-all duration-300 border border-indigo-100 hover:border-transparent group-hover:shadow-md"
        >
          {{ project.status === 'completed' ? 'View Completed Project ->' : 'Open Workspace ->' }}
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { projectService } from '@/services/projectService';
import { memberService } from '@/services/memberService';

const projects = ref([]);
const loading = ref(true);
const joinCode = ref('');
const joining = ref(false);

const loadWorkspace = async () => {
  try {
    projects.value = await projectService.getMyProjects();
  } catch (err) {
    console.error('Failed to load student projects', err);
  } finally {
    loading.value = false;
  }
};

const handleJoin = async () => {
  if (joinCode.value.length < 6) return;
  joining.value = true;
  try {
    await memberService.joinProject({ join_code: joinCode.value });
    joinCode.value = '';
    await loadWorkspace();
  } catch (err) {
    alert(err.response?.data?.error || 'Could not join project. Check your code.');
  } finally {
    joining.value = false;
  }
};

onMounted(loadWorkspace);
</script>
