<template>
  <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
    <div class="mb-8 flex items-center justify-between animate-fade-in">
      <div>
        <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">Managed Students</h1>
        <p class="text-slate-500 mt-1 font-medium">A consolidated roster of all students enrolled in your projects.</p>
      </div>
    </div>

    <!-- Student Roster Table -->
    <div class="glass-panel overflow-hidden sm:rounded-2xl border border-slate-200 shadow-sm animate-slide-up">
      <div class="px-6 py-5 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
        <h3 class="text-lg font-bold text-slate-900 flex items-center gap-2"><span class="text-indigo-500">👨‍🎓</span> Master Roster</h3>
        <div class="flex items-center gap-4">
            <input 
                v-model="searchQuery" 
                type="text" 
                placeholder="Search students..." 
                class="bg-white border border-slate-200 rounded-lg px-4 py-2 text-xs font-medium focus:ring-2 focus:ring-indigo-100 outline-none w-64 shadow-sm"
            />
        </div>
      </div>
      
      <div v-if="loading" class="text-center py-24">
        <div class="w-12 h-12 border-4 border-slate-200 border-t-indigo-600 rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-slate-500 font-medium">Loading roster...</p>
      </div>

      <div v-else-if="filteredRoster.length === 0" class="text-center py-24 text-slate-500 font-medium">
        <p class="text-4xl mb-4">👥</p>
        No students found in your projects.
      </div>
      
      <table v-else class="w-full text-left border-collapse">
        <thead>
          <tr class="bg-slate-50/50 border-b border-slate-100">
            <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Student</th>
            <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Email</th>
            <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Enrolled Projects</th>
            <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="student in filteredRoster" :key="student.id" class="hover:bg-slate-50/50 transition-colors group">
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold text-sm ring-2 ring-white">
                  {{ student.name.charAt(0) }}
                </div>
                <p class="text-sm font-bold text-slate-900">{{ student.name }}</p>
              </div>
            </td>
            <td class="px-6 py-4 text-sm font-medium text-slate-500">
              {{ student.email }}
            </td>
            <td class="px-6 py-4">
              <div class="flex flex-wrap gap-2">
                <span v-for="project in (student.managed_projects || [])" :key="project.id" class="inline-flex items-center gap-2 px-2 py-1 bg-indigo-50 text-indigo-700 text-[10px] font-bold uppercase tracking-wider rounded border border-indigo-100">
                  {{ project.name }}
                  <button @click="revokeProjectAccess(student, project)" class="text-rose-600 hover:text-rose-800 normal-case font-black">Revoke</button>
                </span>
              </div>
            </td>
            <td class="px-6 py-4 text-right">
              <button @click="contactStudent(student)" class="text-indigo-600 hover:text-indigo-800 text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-indigo-50 transition-colors">
                Contact
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { projectService } from '@/services/projectService';

const roster = ref([]);
const loading = ref(true);
const searchQuery = ref('');

const loadData = async () => {
  try {
    roster.value = await projectService.getGlobalRoster();

  } catch (err) {
    console.error("Failed to load global roster", err);
  } finally {
    loading.value = false;
  }
};

const filteredRoster = computed(() => {
    if (!searchQuery.value) return roster.value;
    const s = searchQuery.value.toLowerCase();
    return roster.value.filter(student => 
        student.name.toLowerCase().includes(s) || 
        student.email.toLowerCase().includes(s)
    );
});

const revokeProjectAccess = async (student, project) => {
    if (!confirm(`Revoke ${student.name}'s access from ${project.name}?`)) return;
    try {
        await projectService.removeStudent(project.id, student.id);
        await loadData();
    } catch (err) {
        console.error('Failed to revoke student access', err);
        alert(err.response?.data?.message || 'Failed to revoke access.');
    }
};

const contactStudent = (student) => {
    window.location.href = `mailto:${student.email}`;
};

onMounted(loadData);
</script>


