<template>
  <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
    <div class="mb-8 flex items-start justify-between gap-4 animate-fade-in">
      <div>
        <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">Project Overview</h1>
        <p class="text-slate-500 mt-1 font-medium">Review student submissions, manage access, and close the project when work is complete.</p>
        <div class="mt-3 flex items-center gap-3 flex-wrap">
          <span class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border"
            :class="project?.status === 'completed' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : project?.status === 'archived' ? 'bg-slate-100 text-slate-600 border-slate-200' : 'bg-indigo-50 text-indigo-700 border-indigo-200'">
            {{ project?.status || 'active' }}
          </span>
          <span v-if="project?.join_code" class="text-xs font-mono text-slate-500">Join code: {{ project.join_code }}</span>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <button
          v-if="project?.status === 'active'"
          @click="markProjectCompleted"
          :disabled="closingProject"
          class="px-4 py-2.5 bg-slate-900 text-white rounded-xl text-xs font-black uppercase tracking-widest hover:bg-slate-800 transition-all disabled:opacity-50"
        >
          {{ closingProject ? 'Closing...' : 'Mark Completed & Close' }}
        </button>
      </div>
    </div>

    <!-- Stats Grid -->
    <div v-if="stats" class="grid grid-cols-1 gap-6 sm:grid-cols-3 mb-10 animate-slide-up">
      <div class="glass-card rounded-2xl p-6 border-b-4 border-indigo-500">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center text-xl">📊</div>
          <dt class="text-sm font-bold text-slate-500 uppercase tracking-widest truncate">Average Grade</dt>
        </div>
        <dd class="mt-2 text-4xl font-extrabold text-indigo-600">{{ stats.average_score.toFixed(1) }}<span class="text-lg text-slate-400">/100</span></dd>
      </div>
      <div class="glass-card rounded-2xl p-6 border-b-4 border-blue-500">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-xl">📝</div>
          <dt class="text-sm font-bold text-slate-500 uppercase tracking-widest truncate">Submissions</dt>
        </div>
        <dd class="mt-2 text-4xl font-extrabold text-slate-900">{{ stats.total_submissions }}</dd>
      </div>
      <div class="glass-card rounded-2xl p-6 border-b-4 border-emerald-500">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center text-xl">✅</div>
          <dt class="text-sm font-bold text-slate-500 uppercase tracking-widest truncate">Reviewed</dt>
        </div>
        <dd class="mt-2 text-4xl font-extrabold text-emerald-600">{{ stats.processed_count }}</dd>
      </div>
    </div>

    <!-- Tab Navigation -->
    <div class="flex items-center gap-8 border-b border-slate-200 mb-8 animate-fade-in">
      <button @click="activeTab = 'submissions'" class="pb-4 text-sm font-bold uppercase tracking-widest transition-all relative" :class="activeTab === 'submissions' ? 'text-indigo-600' : 'text-slate-400 hover:text-slate-600'">
        Submissions
        <div v-if="activeTab === 'submissions'" class="absolute bottom-0 left-0 right-0 h-1 bg-indigo-600 rounded-full"></div>
      </button>
      <button @click="activeTab = 'milestones'" class="pb-4 text-sm font-bold uppercase tracking-widest transition-all relative" :class="activeTab === 'milestones' ? 'text-indigo-600' : 'text-slate-400 hover:text-slate-600'">
        Milestones
        <span class="ml-2 px-2 py-0.5 rounded-full text-[10px] bg-indigo-50 text-indigo-600 font-black">{{ milestones.length }}</span>
        <div v-if="activeTab === 'milestones'" class="absolute bottom-0 left-0 right-0 h-1 bg-indigo-600 rounded-full"></div>
      </button>
      <button @click="activeTab = 'roster'" class="pb-4 text-sm font-bold uppercase tracking-widest transition-all relative" :class="activeTab === 'roster' ? 'text-indigo-600' : 'text-slate-400 hover:text-slate-600'">
        Student Roster
        <div v-if="activeTab === 'roster'" class="absolute bottom-0 left-0 right-0 h-1 bg-indigo-600 rounded-full"></div>
      </button>
    </div>

    <!-- Tab 1: Submissions -->
    <div v-if="activeTab === 'submissions'" class="space-y-6">
      <div class="glass-panel overflow-hidden sm:rounded-2xl border border-slate-200 shadow-sm animate-slide-up">
        <div class="px-6 py-5 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
          <h3 class="text-lg font-bold text-slate-900 flex items-center gap-2"><span class="text-indigo-500">📋</span> Received Submissions</h3>
        </div>
        
        <div v-if="submissions.length === 0" class="text-center py-24 text-slate-500 font-medium">
          <p class="text-4xl mb-4">📥</p>
          No submissions received yet for this project.
        </div>
        
        <table v-else class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50/50 border-b border-slate-100">
              <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Student</th>
              <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Upload Date</th>
              <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest text-center">Status</th>
              <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest text-center">Score</th>
              <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="sub in submissions" :key="sub.id" class="hover:bg-slate-50/50 transition-colors group">
              <td class="px-6 py-4">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs">
                    {{ sub.student?.name?.charAt(0) || 'S' }}
                  </div>
                  <div>
                    <p class="text-sm font-bold text-slate-900">{{ sub.student?.name || 'Unknown Student' }}</p>
                    <p class="text-xs text-slate-500 font-medium">{{ sub.student?.email }}</p>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 text-sm font-medium text-slate-500">
                {{ formatDateTime(sub.created_at) }}
              </td>
              <td class="px-6 py-4 text-center">
                <span :class="statusBadge(displayReviewStatus(sub))" class="px-2.5 py-1 rounded-lg text-[10px] font-extrabold uppercase tracking-wider border">
                  {{ formatReviewStatus(displayReviewStatus(sub)) }}
                </span>
              </td>
              <td class="px-6 py-4 text-center">
                <div v-if="sub.grade" class="text-sm font-black text-slate-900">
                  {{ sub.grade }}
                </div>
                <div v-else class="text-xs font-bold text-slate-300 italic">Ungraded</div>
              </td>
                  <td class="px-6 py-4 text-right">
                <div class="flex justify-end gap-2 text-xl">
                  <button @click="downloadPdf(sub.id)" class="p-2 text-slate-400 hover:text-indigo-600 transition-colors" title="Download PDF">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                  </button>
                  <button 
                    v-if="!sub.ai_score && sub.status !== 'processing'"
                    @click="triggerAI(sub)" 
                    class="p-2 text-slate-400 hover:text-emerald-600 transition-colors"
                    :class="loadingSubId === sub.id ? 'animate-pulse' : ''"
                    title="Run AI Analysis"
                  >
                    🤖
                  </button>
                  <button @click="openReviewWorkspace(sub)" class="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 text-xs font-bold rounded-lg hover:bg-slate-50 transition-all shadow-sm">
                    Review
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab 2: Roster -->
    <div v-if="activeTab === 'roster'" class="space-y-6">
      <div class="glass-panel overflow-hidden sm:rounded-2xl border border-slate-200 shadow-sm animate-slide-up">
        <div class="px-6 py-5 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
          <h3 class="text-lg font-bold text-slate-900 flex items-center gap-2"><span class="text-indigo-500">👨‍🎓</span> Enrolled Students</h3>
          <div class="text-xs font-bold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-3 py-1 rounded-full">
            Code: {{ project?.join_code }}
          </div>
        </div>

        <div v-if="roster.length === 0" class="text-center py-24 text-slate-500 font-medium">
          No students joined this project yet.
        </div>

        <table v-else class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50/50 border-b border-slate-100">
              <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Name</th>
              <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Email</th>
              <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Status</th>
              <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="student in roster" :key="student.id" class="hover:bg-slate-50/50 transition-colors">
              <td class="px-6 py-4 text-sm font-bold text-slate-900">{{ student.name }}</td>
              <td class="px-6 py-4 text-sm font-medium text-slate-500">{{ student.email }}</td>
              <td class="px-6 py-4">
                <span class="px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-100 text-[10px] font-extrabold uppercase tracking-wider">Active</span>
              </td>
              <td class="px-6 py-4 text-right">
                <button @click="revokeAccess(student.id)" class="text-rose-600 hover:text-rose-800 text-xs font-bold px-3 py-1.5 rounded-lg hover:bg-rose-50 transition-colors">
                  Revoke Access
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tab: Milestones -->
    <div v-if="activeTab === 'milestones'" class="space-y-6 animate-fade-in">

      <!-- Add Milestone Form -->
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <h3 class="text-sm font-black text-slate-700 uppercase tracking-widest mb-5 flex items-center gap-2">
          <span class="text-indigo-500">➕</span>
          {{ editingMilestone ? 'Edit Milestone' : 'Add New Milestone' }}
          <span v-if="milestones.length >= 10" class="ml-auto text-xs font-bold text-amber-500">Max 10 reached</span>
        </h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="sm:col-span-2">
            <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5">Title *</label>
            <input v-model="msForm.title" type="text" placeholder="e.g. Proposal Draft"
              class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-medium focus:ring-4 focus:ring-indigo-100 focus:border-indigo-500 transition-all outline-none" />
          </div>
          <div class="sm:col-span-2">
            <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5">Description</label>
            <textarea v-model="msForm.description" rows="2" placeholder="Optional instructions for students..."
              class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-medium focus:ring-4 focus:ring-indigo-100 focus:border-indigo-500 transition-all outline-none resize-none"></textarea>
          </div>
          <div>
            <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5">Opens At *</label>
            <input v-model="msForm.starts_at" type="datetime-local"
              class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-medium focus:ring-4 focus:ring-indigo-100 focus:border-indigo-500 transition-all outline-none" />
          </div>
          <div>
            <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1.5">Deadline *</label>
            <input v-model="msForm.deadline" type="datetime-local"
              class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-medium focus:ring-4 focus:ring-indigo-100 focus:border-indigo-500 transition-all outline-none" />
          </div>
        </div>
        <div class="flex items-center gap-3 mt-5">
          <button @click="saveMilestone" :disabled="msSaving || milestones.length >= 10 && !editingMilestone"
            class="px-6 py-2.5 bg-indigo-600 text-white rounded-xl font-black text-xs uppercase tracking-widest hover:bg-indigo-700 transition-all disabled:opacity-50 shadow-lg shadow-indigo-100">
            {{ msSaving ? 'Saving...' : (editingMilestone ? 'Update' : 'Create Milestone') }}
          </button>
          <button v-if="editingMilestone" @click="cancelEdit"
            class="px-6 py-2.5 bg-white border border-slate-200 text-slate-600 rounded-xl font-bold text-xs uppercase tracking-widest hover:bg-slate-50 transition-all">
            Cancel
          </button>
        </div>
      </div>

      <!-- Milestones list -->
      <div v-if="milestones.length === 0" class="text-center py-12 bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-slate-400">
        <p class="text-lg font-bold">No milestones yet.</p>
        <p class="text-sm mt-1">Create your first milestone above.</p>
      </div>
      <div v-else class="space-y-3">
        <div v-for="(m, idx) in milestones" :key="m.id"
          class="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 flex items-start justify-between gap-4">
          <div class="flex items-start gap-4 flex-1 min-w-0">
            <div class="w-9 h-9 rounded-xl flex items-center justify-center text-base flex-shrink-0"
              :class="{ 'bg-green-50': m.state==='active', 'bg-orange-50': m.state==='dormant', 'bg-slate-50': m.state==='locked' }">
              {{ m.state === 'active' ? '🟢' : m.state === 'dormant' ? '🟡' : '🔴' }}
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">#{{ idx + 1 }}</span>
                <span class="px-2 py-0.5 rounded-lg text-[10px] font-black uppercase tracking-wider border"
                  :class="{ 'bg-green-50 text-green-700 border-green-200': m.state==='active', 'bg-orange-50 text-orange-600 border-orange-200': m.state==='dormant', 'bg-slate-50 text-slate-500 border-slate-200': m.state==='locked' }">
                  {{ m.state === 'active' ? 'Active' : m.state === 'dormant' ? 'Upcoming' : 'Closed' }}
                </span>
                <span class="text-xs text-slate-400 font-medium">{{ m.submission_count || 0 }} submitted</span>
              </div>
              <h4 class="font-extrabold text-slate-900 mt-0.5">{{ m.title }}</h4>
              <p class="text-xs text-slate-500 mt-0.5">📅 {{ formatDateTime(m.starts_at) }} → ⏰ {{ formatDateTime(m.deadline) }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            <button @click="startEdit(m)" class="p-2 rounded-lg hover:bg-indigo-50 text-slate-400 hover:text-indigo-600 transition-colors">✏️</button>
            <button @click="deleteMilestone(m.id)" class="p-2 rounded-lg hover:bg-red-50 text-slate-400 hover:text-red-600 transition-colors">🗑️</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Unified Review & Preview Workspace -->
    <SubmissionReviewModal 
        v-if="selectedSub" 
        :submission="selectedSub" 
        :token="authStore.token" 
        @close="selectedSub = null" 
        @saved="loadData" 
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed, reactive } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import { submissionService } from '@/services/submissionService';
import { projectService } from '@/services/projectService';
import api from '@/services/api';
import SubmissionReviewModal from '@/components/common/SubmissionReviewModal.vue';

const route = useRoute();
const authStore = useAuthStore();
const project = ref(null);
const submissions = ref([]);
const roster = ref([]);
const stats = ref(null);
const milestones = ref([]);
const activeTab = ref('submissions');
const loadingSubId = ref(null);
const selectedSub = ref(null);
const closingProject = ref(false);

// Milestone form state
const editingMilestone = ref(null);
const msSaving = ref(false);
const msForm = reactive({ title: '', description: '', starts_at: '', deadline: '' });

const resetMsForm = () => { msForm.title = ''; msForm.description = ''; msForm.starts_at = ''; msForm.deadline = ''; };
const cancelEdit = () => { editingMilestone.value = null; resetMsForm(); };
const startEdit = (m) => {
  editingMilestone.value = m;
  msForm.title = m.title;
  msForm.description = m.description || '';
  // Convert ISO to local datetime-local format
  const toLocal = (iso) => { const d = new Date(iso); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0,16); };
  msForm.starts_at = toLocal(m.starts_at);
  msForm.deadline = toLocal(m.deadline);
};

const loadData = async () => {
  const projectId = route.params.id;
  try {
    const [projData, subData, statData, rosterData, msData] = await Promise.all([
      projectService.getProjectDetails(projectId),
      submissionService.getProjectSubmissions(projectId),
      submissionService.getProjectStats(projectId),
      projectService.getProjectRoster(projectId),
      api.get(`/milestones/project/${projectId}`)
    ]);
    project.value = projData.data;
    submissions.value = subData.submissions;
    stats.value = statData.data;
    roster.value = rosterData;
    milestones.value = msData.data.data || [];
  } catch (err) {
    console.error("Error loading project data", err);
  }
};

const saveMilestone = async () => {
  if (!msForm.title.trim() || !msForm.starts_at || !msForm.deadline) {
    alert('Title, start date, and deadline are required.'); return;
  }
  msSaving.value = true;
  const payload = {
    title: msForm.title,
    description: msForm.description,
    starts_at: new Date(msForm.starts_at).toISOString(),
    deadline: new Date(msForm.deadline).toISOString(),
  };
  try {
    if (editingMilestone.value) {
      await api.patch(`/milestones/${editingMilestone.value.id}`, payload);
    } else {
      await api.post(`/milestones/project/${route.params.id}`, payload);
    }
    cancelEdit();
    await loadData();
  } catch (err) {
    alert(err.response?.data?.message || 'Failed to save milestone.');
  } finally {
    msSaving.value = false;
  }
};

const deleteMilestone = async (id) => {
  if (!confirm('Delete this milestone? All submissions linked to it will also be deleted.')) return;
  try {
    await api.delete(`/milestones/${id}`);
    await loadData();
  } catch (err) {
    alert('Failed to delete milestone.');
  }
};

const triggerAI = async (sub) => {
  loadingSubId.value = sub.id;
  try {
    await submissionService.triggerAIEvaluation(sub.id);
    sub.status = 'pending';
    setTimeout(() => {
        loadData();
        loadingSubId.value = null;
    }, 1500);
  } catch (err) {
    console.error("Failed to trigger AI", err);
    loadingSubId.value = null;
  }
};

const markProjectCompleted = async () => {
  if (!project.value || project.value.status !== 'active') return;
  if (!confirm('Mark this project as completed and close student access? Students will no longer be able to join or submit work to this project.')) return;
  closingProject.value = true;
  try {
    const updated = await projectService.updateProjectStatus(route.params.id, 'completed');
    project.value = updated;
    await loadData();
  } catch (err) {
    console.error('Failed to close project', err);
    alert(err.response?.data?.message || 'Failed to close project.');
  } finally {
    closingProject.value = false;
  }
};

const revokeAccess = async (studentId) => {
  if (!confirm("Are you sure you want to revoke this student's access? They will no longer be able to submit work to this project.")) return;
  try {
    await projectService.removeStudent(route.params.id, studentId);
    roster.value = roster.value.filter(s => s.id !== studentId);
  } catch (err) {
    console.error("Failed to revoke access", err);
  }
};

const openReviewWorkspace = (sub) => {
  selectedSub.value = sub;
};

const downloadPdf = async (id) => {
  try {
    const url = await submissionService.getDownloadUrl(id);
    window.open(url, '_blank');
  } catch (e) {
    console.error('Failed to get download URL', e);
  }
};

const formatDateTime = (dateStr) => {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleString([], { 
    month: 'short', 
    day: 'numeric', 
    hour: '2-digit', 
    minute: '2-digit' 
  });
};

const displayReviewStatus = (sub) => sub.review_status || 'pending_review';

const formatReviewStatus = (status) => {
  const labels = {
    pending_review: 'Pending Review',
    approved: 'Approved',
    needs_revision: 'Needs Revision',
    rejected: 'Rejected',
  };
  return labels[status] || 'Pending Review';
};

const statusBadge = (status) => {
  const classes = {
    pending_review: 'bg-amber-50 text-amber-700 border-amber-200',
    approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    needs_revision: 'bg-blue-50 text-blue-700 border-blue-200',
    rejected: 'bg-rose-50 text-rose-700 border-rose-200',
  };
  return classes[status] || 'bg-slate-50 text-slate-700 border-slate-200';
};

onMounted(loadData);
</script>

