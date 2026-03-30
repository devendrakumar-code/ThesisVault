<template>
  <div class="max-w-5xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">

    <!-- Course Hero Header -->
    <div v-if="project" class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 via-indigo-700 to-violet-800 text-white p-8 shadow-2xl animate-fade-in">
      <div class="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl pointer-events-none"></div>
      <div class="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2 blur-3xl pointer-events-none"></div>
      <div class="relative z-10 flex flex-col md:flex-row md:items-center gap-6">
        <div class="w-16 h-16 rounded-2xl bg-white/15 backdrop-blur-sm flex items-center justify-center text-3xl flex-shrink-0 border border-white/20 shadow-lg">
          🎓
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-3 mb-2">
            <span class="px-3 py-1 bg-white/20 rounded-lg text-[10px] font-black uppercase tracking-widest border border-white/10">Course</span>
            <span class="text-indigo-200 text-xs font-mono">{{ project.join_code }}</span>
          </div>
          <h1 class="text-3xl font-extrabold tracking-tight leading-tight mb-2">{{ project.name }}</h1>
          <p v-if="project.description" class="text-indigo-200 text-sm leading-relaxed max-w-2xl">{{ project.description }}</p>
          <p v-else class="text-indigo-300 text-sm italic">No course description provided.</p>
        </div>
        <div class="flex flex-col gap-2 text-right flex-shrink-0">
          <div class="bg-white/10 border border-white/20 rounded-2xl px-5 py-3 backdrop-blur-sm">
            <p class="text-[10px] font-black text-indigo-200 uppercase tracking-widest mb-1">Milestones</p>
            <p class="text-2xl font-extrabold">{{ milestones.length }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4">
      <div v-for="i in 3" :key="i" class="bg-white rounded-2xl border border-slate-100 p-6 animate-pulse">
        <div class="h-5 bg-slate-200 rounded w-1/3 mb-4"></div>
        <div class="h-3 bg-slate-100 rounded w-2/3"></div>
      </div>
    </div>

    <!-- No milestones yet -->
    <div v-else-if="milestones.length === 0" class="text-center py-16 bg-white rounded-2xl border border-dashed border-slate-200 text-slate-400">
      <div class="text-5xl mb-4">📋</div>
      <p class="font-semibold text-slate-600">No milestones set up yet.</p>
      <p class="text-sm mt-1">Your professor will add submission milestones soon.</p>
    </div>

    <!-- Milestone Cards -->
    <div v-else class="space-y-5 animate-fade-in">
      <h2 class="text-lg font-extrabold text-slate-900 flex items-center gap-3">
        <span class="w-1.5 h-6 bg-indigo-500 rounded-full"></span>
        Submission Milestones
      </h2>

      <div v-for="(m, idx) in milestones" :key="m.id"
           class="bg-white rounded-2xl border shadow-sm overflow-hidden transition-all"
           :class="{
             'border-indigo-200 shadow-indigo-50': m.state === 'active',
             'border-slate-100 opacity-70': m.state === 'dormant',
             'border-slate-200': m.state === 'locked',
           }">

        <!-- Milestone Header -->
        <div class="px-6 pt-5 pb-4 flex items-start gap-4">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xl flex-shrink-0 mt-0.5"
               :class="{
                 'bg-indigo-50 text-indigo-600': m.state === 'active',
                 'bg-slate-50 text-slate-400': m.state === 'dormant',
                 'bg-slate-50 text-slate-400': m.state === 'locked',
               }">
            {{ m.state === 'active' ? '📤' : m.state === 'locked' ? '🔒' : '⏳' }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-3 flex-wrap">
              <span class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Milestone {{ idx + 1 }}</span>
              <span class="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider border"
                    :class="{
                      'bg-green-50 text-green-700 border-green-200': m.state === 'active',
                      'bg-orange-50 text-orange-600 border-orange-200': m.state === 'dormant',
                      'bg-slate-50 text-slate-500 border-slate-200': m.state === 'locked',
                    }">
                {{ m.state === 'active' ? '🟢 Open' : m.state === 'dormant' ? '🟡 Upcoming' : '🔴 Closed' }}
              </span>
            </div>
            <h3 class="text-lg font-extrabold text-slate-900 mt-1">{{ m.title }}</h3>
            <p v-if="m.description" class="text-sm text-slate-500 mt-1 leading-relaxed">{{ m.description }}</p>
          </div>
        </div>

        <!-- Date info strip -->
        <div class="px-6 pb-4 flex flex-wrap gap-4 text-xs font-semibold text-slate-500">
          <span class="flex items-center gap-1.5">
            <span class="text-indigo-400">📅</span>
            Opens: <strong class="text-slate-700">{{ formatDate(m.starts_at) }}</strong>
          </span>
          <span class="flex items-center gap-1.5">
            <span class="text-red-400">⏰</span>
            Deadline: <strong class="text-slate-700">{{ formatDate(m.deadline) }}</strong>
          </span>
        </div>

        <!-- Submitted badge (if student already submitted for this milestone) -->
        <div v-if="m.my_submission" class="mx-6 mb-4 p-4 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <span class="text-2xl">📎</span>
            <div>
              <p class="text-xs font-black text-slate-400 uppercase tracking-widest mb-0.5">Your Submission</p>
              <p class="text-sm font-bold text-slate-800">
                Submitted {{ formatRelativeDate(m.my_submission.created_at) }}
                <span class="ml-2 px-2 py-0.5 rounded-lg text-[10px] font-black uppercase tracking-wider border"
                  :class="reviewStatusStyle(m.my_submission.review_status).badge">
                  {{ reviewStatusStyle(m.my_submission.review_status).label }}
                </span>
              </p>
              <p v-if="m.my_submission.review_status === 'rejected' && m.my_submission.resubmission_deadline" class="text-xs text-red-600 mt-1 font-semibold">
                Resubmit by {{ formatDate(m.my_submission.resubmission_deadline) }}
                <span v-if="m.my_submission.rejection_extension_days" class="text-slate-500 font-medium">({{ m.my_submission.rejection_extension_days }} extra day<span v-if="m.my_submission.rejection_extension_days !== 1">s</span> granted)</span>
              </p>
            </div>
          </div>
          <router-link v-if="m.my_submission.review_status !== 'pending_review'"
            :to="`/student/submission/${m.my_submission.id}`"
            class="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition-colors">
            View Report →
          </router-link>
        </div>

        <!-- Upload zone (active state only) -->
        <div v-if="m.state === 'active' && (!m.my_submission || m.my_submission.review_status === 'pending_review' || m.my_submission.can_resubmit)" class="px-6 pb-6">
          <div class="border-2 border-dashed rounded-xl p-6 text-center transition-colors"
               :class="activeUploadMilestone === m.id ? 'border-indigo-400 bg-indigo-50' : 'border-slate-200 hover:border-indigo-300'">
            <input type="file" :id="`file-${m.id}`" accept="application/pdf" class="hidden"
                   @change="(e) => onFileSelected(e, m.id)" />
            <label :for="`file-${m.id}`" class="cursor-pointer block">
              <div class="text-3xl mb-2">{{ selectedFiles[m.id] ? '📄' : '☁️' }}</div>
              <p class="text-sm font-bold text-slate-700">
                {{ selectedFiles[m.id] ? selectedFiles[m.id].name : uploadPrompt(m) }}
              </p>
              <p class="text-xs text-slate-400 mt-1">PDF only · max 16MB</p>
            </label>
            <button v-if="selectedFiles[m.id]"
              @click="uploadFile(m.id)"
              :disabled="uploading[m.id]"
              class="mt-4 w-full max-w-xs mx-auto py-3 bg-indigo-600 text-white rounded-xl font-black text-xs uppercase tracking-widest shadow-lg shadow-indigo-100 hover:bg-indigo-700 transition-all active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2">
              <span v-if="uploading[m.id]" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              {{ uploading[m.id] ? 'Uploading...' : submitButtonLabel(m) }}
            </button>
          </div>
        </div>

        <!-- Locked message -->
        <div v-else-if="m.state === 'locked' && !m.my_submission" class="px-6 pb-5 text-center">
          <p class="text-sm text-slate-400 italic">Deadline has passed. No submission recorded for this milestone.</p>
        </div>
        <div v-else-if="m.my_submission?.review_status === 'rejected'" class="px-6 pb-5 text-center">
          <p class="text-sm text-slate-500 italic">Your professor flagged this submission for revision/rejection and the extra resubmission window has ended.</p>
        </div>
        <!-- Dormant message -->
        <div v-else-if="m.state === 'dormant'" class="px-6 pb-5">
          <p class="text-sm text-slate-400 italic flex items-center gap-2">
            <span>⏳</span> Opens {{ formatRelativeDate(m.starts_at) }}
          </p>
        </div>

      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import api from '@/services/api';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const project = ref(null);
const milestones = ref([]);
const loading = ref(true);
const selectedFiles = reactive({});
const uploading = reactive({});
const activeUploadMilestone = ref(null);

const fetchData = async () => {
  try {
    const [projRes, msRes] = await Promise.all([
      api.get(`/projects/${route.params.id}`),
      api.get(`/milestones/project/${route.params.id}`)
    ]);
    project.value = projRes.data.data || projRes.data;
    milestones.value = msRes.data.data || [];
  } catch (err) {
    console.error("Failed to load project data", err);
  } finally {
    loading.value = false;
  }
};

const onFileSelected = (event, milestoneId) => {
  const file = event.target.files[0];
  if (file) {
    selectedFiles[milestoneId] = file;
    activeUploadMilestone.value = milestoneId;
  }
};

const uploadFile = async (milestoneId) => {
  const file = selectedFiles[milestoneId];
  if (!file) return;

  uploading[milestoneId] = true;
  const formData = new FormData();
  formData.append('file', file);
  formData.append('milestone_id', milestoneId);

  try {
    await api.post(`/submissions/upload/${route.params.id}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    delete selectedFiles[milestoneId];
    activeUploadMilestone.value = null;
    await fetchData(); // refresh milestone states
  } catch (err) {
    alert(err.response?.data?.message || 'Upload failed. Please try again.');
  } finally {
    uploading[milestoneId] = false;
  }
};

const formatDate = (iso) => {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
};

const formatRelativeDate = (iso) => {
  if (!iso) return '';
  const date = new Date(iso);
  const now = new Date();
  const diffMs = date - now;
  const diffMins = Math.floor(Math.abs(diffMs) / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  const past = diffMs < 0;
  if (diffMins < 60) return past ? `${diffMins}m ago` : `in ${diffMins}m`;
  if (diffHours < 24) return past ? `${diffHours}h ago` : `in ${diffHours}h`;
  if (diffDays < 7) return past ? `${diffDays}d ago` : `in ${diffDays}d`;
  return formatDate(iso);
};

const reviewStatusStyle = (status) => {
  const map = {
    pending_review: { badge: 'bg-slate-100 text-slate-500 border-slate-200', label: '⏳ Pending' },
    approved: { badge: 'bg-green-100 text-green-700 border-green-200', label: '✅ Approved' },
    rejected: { badge: 'bg-red-100 text-red-700 border-red-200', label: '❌ Rejected' },
  };
  return map[status] || map.pending_review;
};

const uploadPrompt = (milestone) => {
  if (!milestone?.my_submission) return 'Click to upload your PDF';
  if (milestone.my_submission.can_resubmit) return 'Upload your corrected PDF for this milestone';
  return 'Upload a newer version for this milestone';
};

const submitButtonLabel = (milestone) => {
  if (milestone?.my_submission?.can_resubmit) return 'Submit Corrected Version';
  return milestone?.my_submission ? 'Resubmit' : 'Submit';
};

onMounted(fetchData);
</script>




