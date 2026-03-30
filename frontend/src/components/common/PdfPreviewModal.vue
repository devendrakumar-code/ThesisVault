<template>
  <div v-if="submissionId" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
    <div class="fixed inset-0 bg-slate-900/60 backdrop-blur-md transition-opacity animate-fade-in" @click="$emit('close')"></div>
    
    <div class="bg-white rounded-3xl w-full max-w-6xl h-[90vh] shadow-2xl z-10 animate-slide-up relative flex flex-col overflow-hidden">
        <!-- Header -->
        <div class="px-8 py-5 border-b border-slate-100 flex items-center justify-between bg-white">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center text-xl">📄</div>
                <div>
                    <h3 class="text-lg font-extrabold text-slate-900 tracking-tight">Thesis Document Viewer</h3>
                    <p class="text-xs text-slate-400 font-medium">Viewing original submission</p>
                </div>
            </div>
            <div class="flex items-center gap-4">
                <a 
                    v-if="pdfUrl"
                    :href="pdfUrl" 
                    target="_blank" 
                    class="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-xs font-bold transition-all flex items-center gap-2"
                >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                    Open in New Tab
                </a>
                <button @click="$emit('close')" class="w-10 h-10 flex items-center justify-center rounded-xl bg-slate-50 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors font-bold text-xl">✕</button>
            </div>
        </div>

        <!-- PDF Content -->
        <div class="flex-1 bg-slate-100 p-4 relative overflow-hidden">
            <iframe 
                v-if="pdfUrl"
                :src="pdfUrl" 
                class="w-full h-full rounded-xl shadow-inner border-0"
                type="application/pdf"
            ></iframe>
            <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-slate-100/80">
                <div class="flex flex-col items-center gap-4">
                    <div class="w-10 h-10 border-4 border-slate-200 border-t-indigo-600 rounded-full animate-spin"></div>
                    <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Generating Secure Access...</p>
                </div>
            </div>
            <div v-if="error" class="absolute inset-0 flex items-center justify-center">
                <div class="text-center p-8 bg-white rounded-3xl shadow-xl border border-slate-100 max-w-sm">
                    <div class="text-4xl mb-4">⚠️</div>
                    <h4 class="text-lg font-black text-slate-900 mb-2">Access Failed</h4>
                    <p class="text-sm text-slate-500 font-medium mb-6">{{ error }}</p>
                    <button @click="$emit('close')" class="w-full py-3 bg-slate-900 text-white rounded-xl font-bold hover:bg-slate-800 transition-all">Close</button>
                </div>
            </div>
        </div>
        
        <!-- Footer / Instructions -->
        <div class="px-8 py-4 bg-slate-50 border-t border-slate-100 flex justify-between items-center">
            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Document Securely Served via ThesisVault DRM</p>
            <button @click="$emit('close')" class="px-6 py-2 bg-white border border-slate-200 text-slate-600 rounded-xl text-xs font-bold hover:bg-slate-50 transition-all">Close Viewer</button>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
import { submissionService } from '@/services/submissionService';

const props = defineProps({
    submissionId: {
        type: String,
        default: null
    }
});

defineEmits(['close']);

const pdfUrl = ref(null);
const loading = ref(false);
const error = ref(null);

const fetchUrl = async () => {
    if (!props.submissionId) return;
    
    loading.value = true;
    error.value = null;
    pdfUrl.value = null;
    
    try {
        const url = await submissionService.getDownloadUrl(props.submissionId, true);
        pdfUrl.value = url;
    } catch (err) {
        console.error("Failed to load PDF preview link", err);
        error.value = "Unable to generate a secure preview link. Please try again.";
    } finally {
        loading.value = false;
    }
};

watch(() => props.submissionId, fetchUrl);
onMounted(fetchUrl);
</script>
