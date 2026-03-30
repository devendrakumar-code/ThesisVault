<template>
  <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
    <div class="mb-8 flex items-center justify-between animate-fade-in">
      <div>
        <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">All Submissions</h1>
        <p class="text-slate-500 mt-1 font-medium">Consolidated view of all work received across all your projects.</p>
      </div>
    </div>

    <div class="glass-panel overflow-hidden sm:rounded-2xl border border-slate-200 shadow-sm animate-slide-up">
      <div class="px-6 py-5 border-b border-slate-100 bg-slate-50 flex justify-between items-center gap-4">
        <h3 class="text-lg font-bold text-slate-900 flex items-center gap-2"><span class="text-indigo-500">&#128203;</span> Global Submission Log</h3>
        <div class="flex items-center gap-4">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search students or projects..."
            class="bg-white border border-slate-200 rounded-lg px-4 py-2 text-xs font-medium focus:ring-2 focus:ring-indigo-100 outline-none w-64 shadow-sm"
          />
        </div>
      </div>

      <div v-if="loading" class="text-center py-24">
        <div class="w-12 h-12 border-4 border-slate-200 border-t-indigo-600 rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-slate-500 font-medium">Loading submissions...</p>
      </div>

      <div v-else-if="projectCount === 0" class="text-center py-24 text-slate-500 font-medium px-6">
        <p class="text-4xl mb-4">&#128194;</p>
        <p class="text-xl font-bold text-slate-900 mb-2">No projects yet</p>
        <p class="mb-6">Create your first project to start receiving student submissions.</p>
        <button @click="router.push({ name: 'professor-dashboard' })" class="btn-primary">Create Project</button>
      </div>

      <div v-else-if="submissions.length === 0" class="text-center py-24 text-slate-500 font-medium px-6">
        <p class="text-4xl mb-4">&#128228;</p>
        <p class="text-xl font-bold text-slate-900 mb-2">No submissions yet</p>
        <p>Your projects are ready, but no students have submitted any work yet.</p>
      </div>

      <div v-else-if="filteredSubmissions.length === 0" class="text-center py-24 text-slate-500 font-medium px-6">
        <p class="text-4xl mb-4">&#128269;</p>
        <p class="text-xl font-bold text-slate-900 mb-2">No matching submissions found</p>
        <p>Try a different student name or project search term.</p>
      </div>

      <table v-else class="w-full text-left border-collapse">
        <thead>
          <tr class="bg-slate-50/50 border-b border-slate-100">
            <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Student</th>
            <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Project</th>
            <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest">Submitted</th>
            <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest text-center">Status</th>
            <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest text-center">Score</th>
            <th class="px-6 py-4 text-xs font-bold text-slate-400 uppercase tracking-widest text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="sub in filteredSubmissions" :key="sub.id" class="hover:bg-slate-50/50 transition-colors group">
            <td class="px-6 py-4">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs ring-2 ring-white">
                  {{ sub.student?.name?.charAt(0) || 'S' }}
                </div>
                <div>
                  <p class="text-sm font-bold text-slate-900">{{ sub.student?.name || 'Unknown' }}</p>
                  <p class="text-[10px] text-slate-400 font-mono">{{ sub.student?.email }}</p>
                </div>
              </div>
            </td>
            <td class="px-6 py-4">
              <span class="px-2 py-1 bg-slate-100 text-slate-600 text-[10px] font-bold uppercase tracking-wider rounded border border-slate-200">
                {{ sub.project_name || 'Project' }}
              </span>
            </td>
            <td class="px-6 py-4 text-xs font-medium text-slate-500">
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
              <div v-else class="text-[10px] font-bold text-slate-300 italic">Ungraded</div>
            </td>
            <td class="px-6 py-4 text-right">
              <div class="flex justify-end gap-2 text-xl">
                <button @click="downloadPdf(sub.id)" class="p-2 text-slate-400 hover:text-indigo-600 transition-colors" title="Download PDF">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                </button>
                <button
                  v-if="!sub.ai_evaluation && sub.status !== 'processing'"
                  @click="triggerAI(sub)"
                  class="p-2 text-slate-400 hover:text-emerald-600 transition-colors"
                  :class="loadingSubId === sub.id ? 'animate-pulse' : ''"
                  title="Run AI Analysis"
                >
                  &#129302;
                </button>
                <button @click="openReviewWorkspace(sub)" class="px-3 py-1.5 bg-white border border-slate-200 text-slate-700 text-[10px] font-bold rounded-lg hover:bg-slate-50 transition-all shadow-sm">
                  Review
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

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
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import { submissionService } from '@/services/submissionService';
import { projectService } from '@/services/projectService';
import SubmissionReviewModal from '@/components/common/SubmissionReviewModal.vue';

const authStore = useAuthStore();
const router = useRouter();
const submissions = ref([]);
const projectCount = ref(0);
const loading = ref(true);
const searchQuery = ref('');
const loadingSubId = ref(null);
const selectedSub = ref(null);

const loadData = async () => {
  loading.value = true;
  try {
    const [submissionResponse, projects] = await Promise.all([
      submissionService.getAllProfessorSubmissions(),
      projectService.getMyProjects(),
    ]);
    submissions.value = submissionResponse.submissions;
    projectCount.value = projects.length;
  } catch (err) {
    console.error('Failed to load global submissions', err);
    submissions.value = [];
    projectCount.value = 0;
  } finally {
    loading.value = false;
  }
};

const filteredSubmissions = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return submissions.value;
  return submissions.value.filter((sub) =>
    sub.student?.name?.toLowerCase().includes(query) ||
    sub.project_name?.toLowerCase().includes(query)
  );
});

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

const triggerAI = async (sub) => {
  loadingSubId.value = sub.id;
  try {
    await submissionService.triggerAIEvaluation(sub.id);
    sub.status = 'pending';
    setTimeout(loadData, 2000);
  } catch (err) {
    console.error('AI trigger failed', err);
  } finally {
    loadingSubId.value = null;
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
  return new Date(dateStr).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
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
