<template>
  <div class="max-w-3xl mx-auto py-10 px-4 sm:px-6 lg:px-8">
    <div v-if="loading" class="text-center py-32 flex flex-col items-center justify-center">
      <div class="w-16 h-16 border-4 border-slate-200 border-t-indigo-600 rounded-full animate-spin mb-6 shadow-sm"></div>
      <h3 class="text-xl font-bold text-slate-800">Loading Submission</h3>
      <p class="mt-2 text-slate-500 font-medium">Fetching your evaluation report...</p>
    </div>

    <div v-else-if="submission" class="space-y-6 animate-fade-in">

      <!-- Status Banner -->
      <div class="rounded-2xl p-6 border-2 flex items-center gap-5 shadow-sm" :class="statusStyles.card">
        <div class="text-4xl">{{ statusStyles.icon }}</div>
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest mb-1" :class="statusStyles.label">Review Status</p>
          <h2 class="text-2xl font-extrabold" :class="statusStyles.title">{{ statusStyles.text }}</h2>
          <p class="text-sm mt-1" :class="statusStyles.sub">{{ statusStyles.description }}</p>
        </div>
      </div>

      <!-- Grade Card -->
      <div v-if="submission.grade" class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 flex items-center gap-6">
        <div class="w-20 h-20 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center">
          <span class="text-3xl font-extrabold text-indigo-700">{{ submission.grade }}</span>
        </div>
        <div>
          <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Final Grade</p>
          <p class="text-lg font-bold text-slate-800">Assigned by your professor</p>
        </div>
      </div>
      <div v-else class="bg-slate-50 rounded-2xl border border-dashed border-slate-200 p-6 text-center text-slate-400 text-sm font-medium">
        Grade not yet assigned
      </div>

      <div v-if="submission.review_status === 'rejected' && submission.resubmission_deadline" class="bg-red-50 rounded-2xl border border-red-200 shadow-sm p-6">
        <h3 class="text-[10px] font-black text-red-500 uppercase tracking-widest mb-3">Resubmission Window</h3>
        <p class="text-base font-bold text-red-800">Resubmit by {{ formatDate(submission.resubmission_deadline) }}</p>
        <p class="mt-2 text-sm text-red-700">Your professor has reopened this milestone for {{ submission.rejection_extension_days || 'a few' }} extra day<span v-if="submission.rejection_extension_days !== 1">s</span>. Upload a corrected version before this deadline.</p>
      </div>

      <!-- Professor Remarks -->
      <div class="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <h3 class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
          <span>✍️</span> Professor Remarks
        </h3>
        <p v-if="submission.remarks" class="text-slate-700 leading-relaxed text-base whitespace-pre-line">{{ submission.remarks }}</p>
        <p v-else class="text-slate-400 italic text-sm">No remarks written yet. Check back after your professor submits their review.</p>
      </div>

      <!-- Actions -->
      <div class="flex flex-col sm:flex-row gap-3">
        <button @click="downloadOriginal" class="flex items-center justify-center gap-2 px-6 py-3 bg-white border border-slate-200 text-slate-600 rounded-xl font-bold text-sm hover:bg-slate-50 transition-all shadow-sm">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
          Download My Submission
        </button>
      </div>

    </div>

    <div v-else class="text-center py-32 text-slate-400">
      <p class="text-lg font-bold">Submission not found.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/authStore';
import api from '@/services/api';
import { submissionService } from '@/services/submissionService';

const route = useRoute();
const authStore = useAuthStore();
const submission = ref(null);
const loading = ref(true);

const fetchSubmission = async () => {
  try {
    const response = await api.get(`/submissions/status/${route.params.id}`);
    submission.value = response.data.data;
  } catch (err) {
    console.error("Failed to load submission report", err);
  } finally {
    loading.value = false;
  }
};

const formatDate = (iso) => {
  if (!iso) return '?';
  return new Date(iso).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
};

const downloadOriginal = async () => {
  try {
    const url = await submissionService.getDownloadUrl(route.params.id);
    window.open(url, '_blank');
  } catch (e) {
    console.error('Failed to get download URL', e);
  }
};

const statusStyles = computed(() => {
  const s = submission.value?.review_status || 'pending_review';
  const map = {
    pending_review: {
      card: 'bg-slate-50 border-slate-200',
      icon: '⏳',
      label: 'text-slate-500',
      title: 'text-slate-800',
      text: 'Awaiting Review',
      sub: 'text-slate-500',
      description: 'Your submission has been received. Your professor will review it shortly.',
    },
    approved: {
      card: 'bg-green-50 border-green-200',
      icon: '✅',
      label: 'text-green-600',
      title: 'text-green-800',
      text: 'Approved',
      sub: 'text-green-600',
      description: 'Congratulations! Your professor has approved your thesis.',
    },
    rejected: {
      card: 'bg-red-50 border-red-300',
      icon: '❌',
      label: 'text-red-600',
      title: 'text-red-800',
      text: 'Rejected',
      sub: 'text-red-600',
      description: submission.value?.resubmission_deadline
        ? `Your professor rejected this version and reopened the milestone until ${formatDate(submission.value.resubmission_deadline)}.`
        : 'Your submission was not accepted. Please review the remarks and resubmit.',
    },
  };
  return map[s] || map.pending_review;
});

onMounted(fetchSubmission);
</script>
