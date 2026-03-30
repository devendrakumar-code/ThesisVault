<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-50 relative overflow-hidden py-12 px-4 sm:px-6 lg:px-8">
    <!-- Decorative background -->
    <div class="absolute top-[-10%] left-[10%] w-96 h-96 bg-indigo-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
    <div class="absolute bottom-[-10%] right-[10%] w-96 h-96 bg-blue-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>

    <div class="max-w-md w-full relative z-10 glass-panel rounded-2xl p-8 animate-slide-up shadow-glass">
      <div class="flex flex-col items-center mb-8">
        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 shadow-md flex items-center justify-center mb-4 transform hover:rotate-12 transition-transform">
          <span class="text-white font-bold text-2xl">T</span>
        </div>
        <h2 class="text-center text-3xl font-extrabold text-slate-900 tracking-tight">Welcome back</h2>
        <p class="mt-2 text-center text-sm text-slate-600">Sign in to ThesisVault</p>
      </div>

      <form class="space-y-6" @submit.prevent="handleLogin">
        <div class="space-y-4">
          <div>
            <label for="email" class="sr-only">Email address</label>
            <input id="email" v-model="email" type="email" required class="input-field" placeholder="Email address" />
          </div>
          <div>
            <label for="password" class="sr-only">Password</label>
            <input id="password" v-model="password" type="password" required class="input-field" placeholder="Password" />
          </div>
        </div>

        <div v-if="error" class="text-red-500 text-sm text-center font-medium bg-red-50/50 rounded-lg py-2">
          {{ error }}
        </div>

        <div>
          <button type="submit" :disabled="loading" class="btn-primary w-full shadow-neon">
            <span v-if="loading" class="flex items-center gap-2">
              <svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              Signing in...
            </span>
            <span v-else>Sign in</span>
          </button>
        </div>
        
        <div class="text-center text-sm mt-4">
          <router-link to="/" class="text-indigo-600 hover:text-indigo-500 font-medium">← Back to Home</router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '@/stores/authStore';
import { useRouter } from 'vue-router';

const email = ref('');
const password = ref('');
const error = ref(null);
const loading = ref(false);

const authStore = useAuthStore();
const router = useRouter();

async function handleLogin() {
  loading.value = true;
  error.value = null;
  try {
    await authStore.login(email.value, password.value);
    router.push({ name: 'dashboard' });
  } catch (err) {
    error.value = err;
  } finally {
    loading.value = false;
  }
}
</script>
