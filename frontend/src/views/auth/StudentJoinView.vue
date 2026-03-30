<template>
  <div class="min-h-screen bg-slate-50 relative overflow-hidden flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="absolute top-[10%] left-[-10%] w-[500px] h-[500px] bg-purple-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>

    <div class="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center mb-6 animate-fade-in">
      <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-md flex items-center justify-center mx-auto mb-4">
        <span class="text-white text-2xl">🎓</span>
      </div>
      <h2 class="text-3xl font-extrabold text-slate-900 tracking-tight">Join a Project</h2>
      <p class="mt-2 text-sm text-slate-600">
        Already have an account? 
        <router-link to="/login" class="text-indigo-600 hover:text-indigo-500 font-bold transition-colors">Sign in</router-link>
      </p>
    </div>

    <div class="mt-2 sm:mx-auto sm:w-full sm:max-w-md relative z-10 animate-slide-up animation-delay-200">
      <div class="glass-panel py-8 px-4 sm:rounded-2xl sm:px-10 shadow-glass">
        <form @submit.prevent="handleStudentJoin" class="space-y-5">
          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1">Project Join Code</label>
            <input v-model="form.join_code" type="text" required placeholder="8-character code" class="input-field text-center tracking-widest uppercase font-mono bg-indigo-50/50" />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">Full Name</label>
              <input v-model="form.name" type="text" required class="input-field" placeholder="John Doe" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">Email</label>
              <input v-model="form.email" type="email" required class="input-field" placeholder="student@edu" />
            </div>
          </div>

          <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1">Password</label>
            <input v-model="form.password" type="password" required class="input-field" placeholder="••••••••" />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">Major</label>
              <input v-model="form.major" type="text" class="input-field" placeholder="e.g. Computer Science" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">Semester</label>
              <input v-model.number="form.semester" type="number" min="1" class="input-field" />
            </div>
          </div>

          <div v-if="error" class="text-red-600 text-sm font-medium bg-red-50/80 backdrop-blur-sm p-3 rounded-lg border border-red-100">
            {{ error }}
          </div>

          <button type="submit" :disabled="loading" class="btn-primary w-full shadow-neon mt-4">
            <span v-if="loading" class="flex items-center gap-2">
              <svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              Creating Account...
            </span>
            <span v-else>Register & Join</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { memberService } from '@/services/memberService';
import { useAuthStore } from '@/stores/authStore';

const router = useRouter();
const authStore = useAuthStore();
const loading = ref(false);
const error = ref(null);

const form = reactive({
  join_code: '',
  email: '',
  password: '',
  name: '',
  major: '',
  semester: 1
});

async function handleStudentJoin() {
  loading.value = true;
  error.value = null;
  try {
    await memberService.studentJoin(form);
    // Automatically log them in after registration
    await authStore.login(form.email, form.password);
    router.push({ name: 'dashboard' });
  } catch (err) {
    error.value = err.response?.data?.error || "Registration failed. Verify your code.";
  } finally {
    loading.value = false;
  }
}
</script>
