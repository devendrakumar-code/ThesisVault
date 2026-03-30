<template>
  <Teleport to="body">
    <div v-if="submission" class="fixed inset-0 z-[9999] flex items-center justify-center p-0 sm:p-4 animate-fade-in font-sans" :class="{ 'cursor-col-resize': isResizing }">
      <div class="fixed inset-0 bg-slate-900/60 backdrop-blur-md transition-opacity" @click="$emit('close')"></div>

      <div class="bg-white lg:rounded-3xl w-full max-w-[98vw] h-full lg:h-[96vh] shadow-2xl z-10 animate-slide-up relative flex flex-col overflow-hidden">
        <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-white/80 backdrop-blur-sm sticky top-0 z-20">
          <div class="flex items-center gap-4">
            <div class="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center text-xl shadow-lg shadow-indigo-200">R</div>
            <div>
              <h3 class="text-lg font-black text-slate-900 leading-none mb-1">Grading Workspace</h3>
              <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                <span class="text-indigo-500">Student</span>
                <span>{{ submission.student?.name || 'Student' }}</span>
                <span class="text-slate-200">|</span>
                <span class="text-indigo-500">Project</span>
                <span>{{ submission.project_name || 'Project' }}</span>
                <span class="text-slate-200">|</span>
                <span class="text-slate-400">Submitted {{ uploadedAt }}</span>
              </p>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <a
              v-if="pdfUrl"
              :href="pdfUrl"
              target="_blank"
              class="hidden sm:flex px-4 py-2 bg-slate-50 hover:bg-slate-100 text-slate-500 rounded-xl text-xs font-bold transition-all items-center gap-2 border border-slate-200/60"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
              New Tab
            </a>
            <button @click="$emit('close')" class="w-10 h-10 flex items-center justify-center rounded-xl bg-slate-50 text-slate-400 hover:bg-indigo-50 hover:text-indigo-600 transition-all font-bold text-xl">�</button>
          </div>
        </div>

        <div ref="workspaceRef" class="flex-1 flex flex-col lg:flex-row overflow-hidden bg-slate-50 relative">
          <div
            class="hidden lg:block relative bg-slate-200 overflow-hidden border-r border-slate-200 shadow-inner"
            :style="{ width: splitPercent + '%' }"
          >
            <div v-if="isResizing" class="absolute inset-0 z-50"></div>

            <iframe
              v-if="pdfUrl"
              :src="pdfUrl"
              class="w-full h-full border-0"
              type="application/pdf"
            ></iframe>
            <div v-if="loadingUrl" class="absolute inset-0 flex items-center justify-center bg-slate-100/80">
              <div class="flex flex-col items-center gap-4">
                <div class="w-10 h-10 border-4 border-slate-200 border-t-indigo-600 rounded-full animate-spin"></div>
                <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Generating Secure Access...</p>
              </div>
            </div>
          </div>

          <div
            class="hidden lg:flex w-2 h-full cursor-col-resize hover:bg-indigo-400 transition-colors bg-slate-200/50 items-center justify-center relative group z-30"
            @mousedown="startResize"
          >
            <div class="w-0.5 h-12 bg-slate-400 group-hover:bg-white rounded-full transition-colors"></div>
            <div class="absolute inset-y-0 -left-2 -right-2"></div>
          </div>

          <div class="flex-1 lg:hidden bg-slate-200 h-1/2 overflow-hidden border-b border-slate-200">
            <iframe
              v-if="pdfUrl"
              :src="pdfUrl"
              class="w-full h-full border-0"
              type="application/pdf"
            ></iframe>
            <div v-if="loadingUrl" class="absolute inset-0 flex items-center justify-center bg-slate-100/80">
              <div class="w-8 h-8 border-4 border-slate-200 border-t-indigo-600 rounded-full animate-spin"></div>
            </div>
          </div>

          <div
            class="w-full bg-white flex flex-col shadow-2xl relative z-10 min-w-[350px]"
            :style="lgScreen ? { width: (100 - splitPercent) + '%' } : {}"
          >
            <div class="flex border-b border-slate-100 px-4 pt-4 bg-slate-50/50">
              <button
                @click="activeTab = 'review'"
                :class="activeTab === 'review' ? 'text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-400 hover:text-slate-600'"
                class="px-4 pb-3 text-xs font-black uppercase tracking-widest transition-all"
              >
                Review
              </button>
              <button
                @click="activeTab = 'analysis'"
                :class="activeTab === 'analysis' ? 'text-indigo-600 border-b-2 border-indigo-600' : 'text-slate-400 hover:text-slate-600'"
                class="px-4 pb-3 text-xs font-black uppercase tracking-widest transition-all"
              >
                AI Insights
              </button>
            </div>

            <div class="flex-1 overflow-y-auto p-6 custom-scrollbar">
              <div v-if="activeTab === 'review'" class="space-y-8 animate-fade-in">
                <div>
                  <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Grade</label>
                  <input
                    v-model="form.grade"
                    type="text"
                    placeholder="e.g. A, B+, 78%"
                    class="w-full bg-slate-50 border border-slate-200 rounded-2xl p-4 text-sm font-medium focus:ring-4 focus:ring-indigo-100 focus:border-indigo-500 transition-all outline-none shadow-inner"
                  />
                </div>
                <div>
                  <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Review Status</label>
                  <select
                    v-model="form.review_status"
                    class="w-full bg-slate-50 border border-slate-200 rounded-2xl p-4 text-sm font-medium focus:ring-4 focus:ring-indigo-100 focus:border-indigo-500 transition-all outline-none shadow-inner"
                  >
                    <option value="pending_review">Pending Review</option>
                    <option value="approved">Approved</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </div>
                <div v-if="form.review_status === 'rejected'">
                  <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Extra Time For Resubmission (Days)</label>
                  <input
                    v-model="form.rejection_extension_days"
                    type="number"
                    min="1"
                    step="1"
                    placeholder="Enter extra days allowed to resubmit"
                    class="w-full bg-slate-50 border border-slate-200 rounded-2xl p-4 text-sm font-medium focus:ring-4 focus:ring-indigo-100 focus:border-indigo-500 transition-all outline-none shadow-inner"
                  />
                  <p class="mt-2 text-xs text-slate-500 leading-relaxed">The student will see the submission as rejected and can upload a new version until this extended window closes.</p>
                </div>
                <div>
                  <label class="block text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Professor Remarks</label>
                  <textarea
                    v-model="form.remarks"
                    rows="12"
                    placeholder="Write your detailed feedback for the student here..."
                    class="w-full bg-slate-50 border border-slate-200 rounded-2xl p-5 text-sm font-medium focus:ring-4 focus:ring-indigo-100 focus:border-indigo-500 transition-all outline-none leading-relaxed shadow-inner"
                  ></textarea>
                </div>
              </div>

              <div v-if="activeTab === 'analysis'" class="space-y-5 animate-fade-in relative min-h-[400px]">
                <div v-if="submission.ai_evaluation" class="space-y-5">
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="p-4 bg-gradient-to-r from-indigo-50 to-violet-50 rounded-2xl border border-indigo-100">
                      <p class="text-[10px] font-black text-indigo-500 uppercase tracking-widest mb-1">AI Score</p>
                      <p class="text-3xl font-black text-indigo-700">{{ submission.ai_score ?? '�' }}<span class="text-base text-indigo-400 font-bold">/100</span></p>
                    </div>
                    <div class="p-4 bg-slate-50 rounded-2xl border border-slate-100">
                      <p class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Plagiarism Risk</p>
                      <p class="text-lg font-black text-slate-900">{{ plagiarismLabel }}</p>
                      <p v-if="submission.ai_evaluation.confidence_note" class="mt-2 text-xs text-slate-500 leading-relaxed">{{ submission.ai_evaluation.confidence_note }}</p>
                    </div>
                  </div>

                  <div class="p-5 bg-slate-50 rounded-2xl border border-slate-100">
                    <h4 class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Executive Summary</h4>
                    <p class="text-sm text-slate-700 leading-relaxed">{{ submission.ai_evaluation.executive_summary || submission.ai_evaluation.summary || 'No summary generated yet.' }}</p>
                  </div>

                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="p-5 bg-slate-50 rounded-2xl border border-slate-100">
                      <h4 class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Document Focus</h4>
                      <p class="text-sm text-slate-700 leading-relaxed">{{ submission.ai_evaluation.document_focus || 'Not available.' }}</p>
                    </div>
                    <div class="p-5 bg-slate-50 rounded-2xl border border-slate-100">
                      <h4 class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Methodology Overview</h4>
                      <p class="text-sm text-slate-700 leading-relaxed">{{ submission.ai_evaluation.methodology_overview || 'Not available.' }}</p>
                    </div>
                  </div>

                  <div v-if="keyFindings.length" class="p-5 bg-slate-50 rounded-2xl border border-slate-100">
                    <h4 class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3">Key Findings</h4>
                    <ul class="space-y-2 text-sm text-slate-700 leading-relaxed">
                      <li v-for="item in keyFindings" :key="item" class="flex gap-2"><span class="text-indigo-500">�</span><span>{{ item }}</span></li>
                    </ul>
                  </div>

                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="p-5 bg-emerald-50 rounded-2xl border border-emerald-100">
                      <h4 class="text-[10px] font-black text-emerald-600 uppercase tracking-widest mb-3">Strengths</h4>
                      <ul class="space-y-2 text-sm text-slate-700 leading-relaxed">
                        <li v-for="item in strengths" :key="item" class="flex gap-2"><span class="text-emerald-500">�</span><span>{{ item }}</span></li>
                      </ul>
                    </div>
                    <div class="p-5 bg-amber-50 rounded-2xl border border-amber-100">
                      <h4 class="text-[10px] font-black text-amber-600 uppercase tracking-widest mb-3">Weaknesses</h4>
                      <ul class="space-y-2 text-sm text-slate-700 leading-relaxed">
                        <li v-for="item in weaknesses" :key="item" class="flex gap-2"><span class="text-amber-500">�</span><span>{{ item }}</span></li>
                      </ul>
                    </div>
                  </div>

                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="p-5 bg-rose-50 rounded-2xl border border-rose-100">
                      <h4 class="text-[10px] font-black text-rose-600 uppercase tracking-widest mb-3">Risks</h4>
                      <ul class="space-y-2 text-sm text-slate-700 leading-relaxed">
                        <li v-for="item in risks" :key="item" class="flex gap-2"><span class="text-rose-500">�</span><span>{{ item }}</span></li>
                      </ul>
                    </div>
                    <div class="p-5 bg-blue-50 rounded-2xl border border-blue-100">
                      <h4 class="text-[10px] font-black text-blue-600 uppercase tracking-widest mb-3">Recommended Next Actions</h4>
                      <ul class="space-y-2 text-sm text-slate-700 leading-relaxed">
                        <li v-for="item in improvementActions" :key="item" class="flex gap-2"><span class="text-blue-500">�</span><span>{{ item }}</span></li>
                      </ul>
                    </div>
                  </div>

                  <div v-if="professorQuestions.length" class="p-5 bg-violet-50 rounded-2xl border border-violet-100">
                    <h4 class="text-[10px] font-black text-violet-600 uppercase tracking-widest mb-3">Questions for Viva or Discussion</h4>
                    <ul class="space-y-2 text-sm text-slate-700 leading-relaxed">
                      <li v-for="item in professorQuestions" :key="item" class="flex gap-2"><span class="text-violet-500">�</span><span>{{ item }}</span></li>
                    </ul>
                  </div>
                </div>
                <div v-else class="flex flex-col items-center justify-center pt-20 pb-12 px-6 text-center">
                  <h4 class="text-lg font-black text-slate-900 mb-2">No AI Review Yet</h4>
                  <button @click="triggerAIEval" :disabled="generatingAI" class="w-full max-w-[200px] py-4 bg-indigo-600 text-white rounded-2xl font-black text-xs uppercase tracking-widest">
                    {{ generatingAI ? 'Analyzing...' : 'Generate Insights' }}
                  </button>
                </div>
              </div>
            </div>

            <div class="p-6 bg-slate-50/80 backdrop-blur-sm border-t border-slate-100 flex flex-col gap-3">
              <button @click="submitReview" :disabled="saving" class="w-full py-4 bg-indigo-600 text-white rounded-2xl font-black text-xs uppercase tracking-widest">
                {{ saving ? 'Saving...' : saveButtonLabel }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { submissionService } from '@/services/submissionService';

const props = defineProps({
  submission: { type: Object, default: null }
});

const emit = defineEmits(['close', 'saved']);

const workspaceRef = ref(null);
const splitPercent = ref(localStorage.getItem('review_split') ? parseFloat(localStorage.getItem('review_split')) : 70);
const isResizing = ref(false);
const lgScreen = ref(window.innerWidth >= 1024);

const startResize = () => {
  isResizing.value = true;
  document.addEventListener('mousemove', handleResize);
  document.addEventListener('mouseup', stopResize);
};

const handleResize = (e) => {
  if (!isResizing.value || !workspaceRef.value) return;
  const rect = workspaceRef.value.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const percentage = (x / rect.width) * 100;
  if (percentage >= 30 && percentage <= 80) {
    splitPercent.value = percentage;
    localStorage.setItem('review_split', percentage);
  }
};

const stopResize = () => {
  isResizing.value = false;
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
};

const updateScreenSize = () => { lgScreen.value = window.innerWidth >= 1024; };

onMounted(() => {
  window.addEventListener('resize', updateScreenSize);
  fetchPdfUrl();
});

onUnmounted(() => {
  window.removeEventListener('resize', updateScreenSize);
  stopResize();
});

const activeTab = ref('review');
const saving = ref(false);
const generatingAI = ref(false);
const form = ref({ grade: '', remarks: '', review_status: 'pending_review', rejection_extension_days: '' });

const pdfUrl = ref(null);
const loadingUrl = ref(false);

const fetchPdfUrl = async () => {
  if (!props.submission?.id) return;
  loadingUrl.value = true;
  try {
    const url = await submissionService.getDownloadUrl(props.submission.id, true);
    pdfUrl.value = url;
  } catch (e) {
    console.error('Failed to fetch signed PDF URL', e);
  } finally {
    loadingUrl.value = false;
  }
};

watch(() => props.submission?.id, fetchPdfUrl);

watch(() => props.submission, (newVal) => {
  if (newVal) {
    form.value = {
      grade: newVal.grade || '',
      remarks: newVal.remarks || '',
      review_status: newVal.review_status || 'pending_review',
      rejection_extension_days: newVal.rejection_extension_days ?? '',
    };
  }
}, { immediate: true });

const uploadedAt = computed(() => {
  if (!props.submission?.created_at) return 'Unknown';
  return new Date(props.submission.created_at).toLocaleDateString();
});

const analysis = computed(() => props.submission?.ai_evaluation || {});
const keyFindings = computed(() => Array.isArray(analysis.value.key_findings) ? analysis.value.key_findings : []);
const strengths = computed(() => Array.isArray(analysis.value.strengths) ? analysis.value.strengths : []);
const weaknesses = computed(() => Array.isArray(analysis.value.weaknesses) ? analysis.value.weaknesses : []);
const risks = computed(() => Array.isArray(analysis.value.risks) ? analysis.value.risks : []);
const improvementActions = computed(() => Array.isArray(analysis.value.improvement_actions) ? analysis.value.improvement_actions : []);
const professorQuestions = computed(() => Array.isArray(analysis.value.professor_questions) ? analysis.value.professor_questions : []);
const plagiarismLabel = computed(() => {
  const value = analysis.value.plagiarism_risk;
  if (!value) return 'Not available';
  return String(value).charAt(0).toUpperCase() + String(value).slice(1);
});

const triggerAIEval = async (isRetry = false) => {
  generatingAI.value = true;
  try {
    await submissionService.triggerAIEvaluation(props.submission.id, isRetry);
    emit('saved');
  } catch (err) {
    console.error('AI Analysis failed', err);
  } finally {
    generatingAI.value = false;
  }
};

const saveButtonLabel = computed(() => {
  if (form.value.review_status === 'approved') return 'Save Approval';
  if (form.value.review_status === 'rejected') return 'Save Rejection';
  return 'Save Review';
});

const submitReview = async () => {
  saving.value = true;
  try {
    const payload = {
      grade: form.value.grade,
      remarks: form.value.remarks,
      review_status: form.value.review_status,
      rejection_extension_days: form.value.review_status === 'rejected'
        ? parseInt(form.value.rejection_extension_days) || 0
        : null,
    };
    await submissionService.reviewSubmission(props.submission.id, payload);
    emit('saved');
    emit('close');
  } catch (err) {
    console.error('Save failed', err);
    alert(err.response?.data?.message || 'Unable to save review. Please try again.');
  } finally {
    saving.value = false;
  }
};
</script>

<style scoped>
.animate-fade-in { animation: fadeIn 0.3s ease-out forwards; }
.animate-slide-up { animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
</style>
