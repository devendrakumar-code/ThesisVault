<template>
  <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-10 gap-4 animate-fade-in">
      <div>
        <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">My Research Projects</h1>
        <p class="text-slate-500 mt-1 font-medium">Manage your active assignments and evaluate theses.</p>
      </div>
      <button @click="openCreateModal" class="btn-primary shadow-neon flex items-center gap-2">
        <span class="text-xl">+</span> New Project
      </button>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="i in 3" :key="i" class="glass-card h-48 rounded-2xl animate-pulse bg-white/50">
        <div class="h-6 bg-slate-200 rounded w-3/4 mx-5 mt-6 mb-4"></div>
        <div class="h-4 bg-slate-200 rounded w-1/2 mx-5 mb-8"></div>
        <div class="h-10 bg-slate-100 rounded-xl mx-5 mt-auto mb-5"></div>
      </div>
    </div>

    <div v-else-if="projects.length === 0" class="text-center py-20 glass-panel rounded-3xl border-2 border-dashed border-indigo-200 animate-slide-up">
      <div class="w-20 h-20 bg-indigo-50 text-indigo-500 rounded-full flex items-center justify-center text-4xl mx-auto mb-6">&#128194;</div>
      <h3 class="text-xl font-bold text-slate-900 mb-2">No projects yet</h3>
      <p class="text-slate-500 font-medium mb-6">Create your first research project to generate a join code and start receiving submissions.</p>
      <button @click="openCreateModal" class="btn-primary">Create Project</button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="(project, index) in projects" :key="project.id" class="glass-card rounded-2xl flex flex-col justify-between overflow-hidden group animate-slide-up" :class="`animation-delay-${(index%3)*200}`">
        <div class="p-6">
          <div class="flex items-start justify-between mb-4 gap-4">
            <div>
              <h3 class="text-xl font-bold text-slate-900 leading-tight group-hover:text-indigo-600 transition-colors">{{ project.name }}</h3>
              <p v-if="project.problem_statement_file_url" class="mt-2 text-xs font-semibold text-slate-500">Problem statement attached</p>
            </div>
            <span :class="statusClass(project.status)" class="px-3 py-1 text-xs font-bold uppercase tracking-widest rounded-full shadow-sm border whitespace-nowrap">
              {{ project.status }}
            </span>
          </div>
          <div class="mt-6 p-4 bg-slate-50 border border-slate-100 rounded-xl">
            <p class="text-xs text-slate-400 uppercase tracking-widest font-bold mb-2">Student Join Code</p>
            <div class="flex items-center justify-between gap-3">
              <code class="text-2xl font-mono font-extrabold text-indigo-600 tracking-widest bg-indigo-50 px-2 py-1 rounded-md border border-indigo-100">{{ project.join_code }}</code>
              <button @click="copyCode(project.join_code, $event)" class="w-10 h-10 rounded-lg flex items-center justify-center text-slate-400 hover:text-indigo-600 hover:bg-white shadow-sm border border-transparent hover:border-slate-200 transition-all active:scale-95" title="Copy code">
                &#128203;
              </button>
            </div>
          </div>
        </div>
        <div class="bg-indigo-50/50 p-4 border-t border-indigo-50 transition-colors group-hover:bg-indigo-50">
          <router-link :to="`/projects/${project.id}`" class="w-full flex items-center justify-center gap-2 font-bold text-indigo-600 hover:text-indigo-800 transition-colors py-2">
            View Submissions <span class="group-hover:translate-x-1 transition-transform">&#8594;</span>
          </router-link>
        </div>
      </div>
    </div>

    <div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-0">
      <div class="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity animate-fade-in" @click="showCreateModal = false"></div>

      <div class="bg-white rounded-3xl shadow-2xl p-8 w-full max-w-3xl z-10 animate-slide-up relative overflow-hidden max-h-[90vh] overflow-y-auto">
        <div class="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-indigo-500 to-blue-500"></div>
        <h3 class="text-2xl font-extrabold text-slate-900 mb-2">Create New Project</h3>
        <p class="text-slate-500 font-medium mb-6">Name the project, provide the problem statement, and set milestone windows before students join.</p>

        <form @submit.prevent="handleCreate" class="space-y-6">
          <div>
            <label class="block text-sm font-bold text-slate-700 mb-2">Project Name</label>
            <input v-model="projectForm.name" type="text" required placeholder="e.g. CS401 Fall Final Thesis" class="input-field shadow-inner bg-slate-50 text-lg py-3" />
          </div>

          <div>
            <label class="block text-sm font-bold text-slate-700 mb-2">Problem Statement</label>
            <textarea v-model="projectForm.description" rows="4" placeholder="Describe the research brief, expected deliverables, constraints, and evaluation focus areas." class="input-field shadow-inner bg-slate-50"></textarea>
          </div>

          <div>
            <label class="block text-sm font-bold text-slate-700 mb-2">Problem Statement PDF</label>
            <input type="file" accept="application/pdf" @change="handleProblemStatementFile" class="block w-full text-sm text-slate-500 file:mr-4 file:rounded-xl file:border-0 file:bg-indigo-50 file:px-4 file:py-2 file:font-bold file:text-indigo-600 hover:file:bg-indigo-100" />
            <p class="mt-2 text-xs text-slate-500">Upload an optional PDF brief for students. PDF only.</p>
            <p v-if="problemStatementFileName" class="mt-2 text-xs font-semibold text-indigo-600">Selected: {{ problemStatementFileName }}</p>
          </div>

          <div class="rounded-2xl border border-slate-200 bg-slate-50/80 p-5">
            <div class="flex items-center justify-between gap-4 mb-4">
              <div>
                <h4 class="text-lg font-bold text-slate-900">Milestones</h4>
                <p class="text-sm text-slate-500">Set the submission phases and deadlines for this project.</p>
              </div>
              <button type="button" @click="addMilestone" :disabled="projectForm.milestones.length >= maxMilestones" class="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed">
                Add Milestone
              </button>
            </div>

            <div v-if="projectForm.milestones.length === 0" class="rounded-xl border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500">
              No milestones added yet. You can create the project without milestones, or add them now.
            </div>

            <div v-else class="space-y-4">
              <div v-for="(milestone, index) in projectForm.milestones" :key="milestone.localId" class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div class="flex items-center justify-between gap-4 mb-4">
                  <h5 class="text-sm font-black uppercase tracking-widest text-slate-500">Milestone {{ index + 1 }}</h5>
                  <button type="button" @click="removeMilestone(index)" class="text-xs font-bold text-rose-600 hover:text-rose-700">Remove</button>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div class="md:col-span-2">
                    <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Title</label>
                    <input v-model="milestone.title" type="text" placeholder="e.g. Proposal Submission" class="input-field bg-slate-50" />
                  </div>
                  <div class="md:col-span-2">
                    <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Description</label>
                    <textarea v-model="milestone.description" rows="2" placeholder="Optional milestone instructions for students." class="input-field bg-slate-50"></textarea>
                  </div>
                  <div>
                    <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Starts At</label>
                    <input v-model="milestone.starts_at" type="datetime-local" class="input-field bg-slate-50" />
                  </div>
                  <div>
                    <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Deadline</label>
                    <input v-model="milestone.deadline" type="datetime-local" class="input-field bg-slate-50" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="createError" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            {{ createError }}
          </div>

          <div class="flex flex-col-reverse sm:flex-row gap-3">
            <button type="button" @click="showCreateModal = false" class="btn-secondary flex-1">Cancel</button>
            <button type="submit" class="btn-primary flex-1 shadow-neon" :disabled="creating || !projectForm.name.trim()">
              {{ creating ? 'Creating Project...' : 'Create Project' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { projectService } from '@/services/projectService';

const maxMilestones = 10;
const projects = ref([]);
const loading = ref(true);
const creating = ref(false);
const showCreateModal = ref(false);
const createError = ref('');
const problemStatementFileName = ref('');
const projectForm = ref(createEmptyProjectForm());

function createMilestone() {
  const now = new Date();
  const start = new Date(now.getTime() + 60 * 60 * 1000);
  const end = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
  return {
    localId: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    title: '',
    description: '',
    starts_at: toLocalDateTime(start),
    deadline: toLocalDateTime(end),
  };
}

function createEmptyProjectForm() {
  return {
    name: '',
    description: '',
    problemStatementFile: null,
    milestones: [createMilestone()],
  };
}

function toLocalDateTime(date) {
  const local = new Date(date);
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return local.toISOString().slice(0, 16);
}

const openCreateModal = () => {
  createError.value = '';
  showCreateModal.value = true;
};

const resetCreateForm = () => {
  projectForm.value = createEmptyProjectForm();
  problemStatementFileName.value = '';
  createError.value = '';
};

const fetchProjects = async () => {
  loading.value = true;
  try {
    projects.value = await projectService.getMyProjects();
  } catch (err) {
    projects.value = [];
  } finally {
    loading.value = false;
  }
};

const handleProblemStatementFile = (event) => {
  const file = event.target.files?.[0] || null;
  projectForm.value.problemStatementFile = file;
  problemStatementFileName.value = file?.name || '';
};

const addMilestone = () => {
  if (projectForm.value.milestones.length >= maxMilestones) return;
  projectForm.value.milestones.push(createMilestone());
};

const removeMilestone = (index) => {
  projectForm.value.milestones.splice(index, 1);
};

const handleCreate = async () => {
  creating.value = true;
  createError.value = '';

  try {
    const milestones = projectForm.value.milestones.map((milestone) => ({
      title: milestone.title.trim(),
      description: milestone.description.trim(),
      starts_at: new Date(milestone.starts_at).toISOString(),
      deadline: new Date(milestone.deadline).toISOString(),
    })).filter((milestone) => milestone.title || milestone.description);

    await projectService.createProject({
      name: projectForm.value.name,
      description: projectForm.value.description,
      problemStatementFile: projectForm.value.problemStatementFile,
      milestones,
    });

    showCreateModal.value = false;
    resetCreateForm();
    await fetchProjects();
  } catch (err) {
    createError.value = err.response?.data?.message || 'Unable to create project right now.';
  } finally {
    creating.value = false;
  }
};

const statusClass = (status) => {
  if (status === 'active') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  return 'bg-slate-50 text-slate-700 border-slate-200';
};

const copyCode = (code, event) => {
  navigator.clipboard.writeText(code);
  const btn = event.currentTarget;
  const original = btn.innerHTML;
  btn.innerHTML = '&#10003;';
  setTimeout(() => {
    btn.innerHTML = original;
  }, 2000);
};

onMounted(fetchProjects);
</script>
