<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-50 py-12 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
    <!-- Abstract Background shapes -->
    <div class="absolute top-0 left-0 w-full h-full pointer-events-none overflow-hidden">
      <div class="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-100 rounded-full blur-[120px] opacity-60"></div>
      <div class="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-100 rounded-full blur-[120px] opacity-60"></div>
    </div>

    <div class="max-w-md w-full space-y-8 relative z-10 glass-panel p-8 sm:p-12 rounded-3xl shadow-glass border-t border-white/50">
      <div class="text-center animate-fade-in">
        <div class="mx-auto h-16 w-16 bg-white rounded-2xl shadow-sm border border-slate-100 flex items-center justify-center text-3xl mb-4">🎓</div>
        <h2 class="text-3xl font-extrabold text-slate-900 tracking-tight">Join Your Institution</h2>
        <p class="mt-3 text-slate-500 font-medium">Complete your professor profile to get started.</p>
      </div>

      <div v-if="loading" class="flex flex-col items-center justify-center py-10 space-y-4 animate-pulse">
        <div class="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
        <p class="text-slate-400 font-bold uppercase tracking-widest text-xs">Verifying Invitation...</p>
      </div>

      <div v-else-if="error" class="animate-shake">
        <div class="bg-rose-50 border border-rose-100 text-rose-700 p-6 rounded-2xl text-center">
          <div class="text-4xl mb-3">⚠️</div>
          <p class="font-bold text-lg mb-2">Invitation Error</p>
          <p class="text-sm opacity-80 mb-6">{{ error }}</p>
          <router-link to="/login" class="btn-primary inline-block px-8">Back to Login</router-link>
        </div>
      </div>

      <form v-else @submit.prevent="handleOnboarding" class="mt-10 space-y-6 animate-slide-up">
        <div class="space-y-4">
          <!-- Email (Read-only) -->
          <div>
            <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5 ml-1">Email Address</label>
            <input 
              v-model="onboardingForm.email" 
              type="email" 
              disabled 
              class="input-field bg-slate-50/50 text-slate-400 cursor-not-allowed border-dashed" 
            />
          </div>

          <!-- Full Name -->
          <div>
            <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5 ml-1">Full Name</label>
            <input 
              v-model="onboardingForm.name" 
              type="text" 
              required 
              placeholder="Dr. Jane Doe" 
              class="input-field" 
            />
          </div>

          <!-- Department -->
          <div>
            <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5 ml-1">Academic Department</label>
            <input 
              v-model="onboardingForm.department" 
              type="text" 
              required 
              placeholder="Computer Science & Engineering" 
              class="input-field" 
            />
          </div>

          <!-- Password -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5 ml-1">Password</label>
              <input 
                v-model="onboardingForm.password" 
                type="password" 
                required 
                placeholder="••••••••" 
                class="input-field" 
              />
            </div>
            <div>
              <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-1.5 ml-1">Confirm</label>
              <input 
                v-model="onboardingForm.confirmPassword" 
                type="password" 
                required 
                placeholder="••••••••" 
                class="input-field" 
              />
            </div>
          </div>
        </div>

        <div v-if="status" :class="status.success ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-rose-50 text-rose-700 border-rose-100'" class="p-4 rounded-xl text-sm font-bold border animate-fade-in flex items-center gap-3">
          <span v-if="status.success">✅</span>
          <span v-else>❌</span>
          {{ status.text }}
        </div>

        <div>
          <button 
            type="submit" 
            :disabled="processing" 
            class="group relative w-full flex justify-center py-3.5 px-4 border border-transparent text-sm font-extrabold rounded-xl text-white btn-primary shadow-neon focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all duration-300 transform hover:-translate-y-0.5"
          >
            <span v-if="processing" class="absolute left-0 inset-y-0 flex items-center pl-3">
              <div class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            </span>
            {{ processing ? 'Setting up account...' : 'Complete Registration' }}
          </button>
        </div>
      </form>

      <div class="text-center mt-6">
        <router-link to="/login" class="text-sm font-bold text-slate-400 hover:text-indigo-600 transition-colors uppercase tracking-widest">
          Already have an account? Log in
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { memberService } from '@/services/memberService';

const route = useRoute();
const router = useRouter();
const token = route.query.token;

const loading = ref(true);
const processing = ref(false);
const error = ref(null);
const status = ref(null);

const onboardingForm = reactive({
  token: token,
  email: '',
  name: '',
  department: '',
  password: '',
  confirmPassword: ''
});

onMounted(async () => {
  if (!token) {
    error.value = "No invitation token found in the URL. Please check your email link.";
    loading.value = false;
    return;
  }

  try {
    const details = await memberService.getInviteDetails(token);
    onboardingForm.email = details.email;
    onboardingForm.name = details.name || '';
    loading.value = false;
  } catch (err) {
    error.value = err.response?.data?.error || "This invitation link is invalid or has expired.";
    loading.value = false;
  }
});

const handleOnboarding = async () => {
  if (onboardingForm.password !== onboardingForm.confirmPassword) {
    status.value = { success: false, text: "Passwords do not match." };
    return;
  }

  if (onboardingForm.password.length < 8) {
    status.value = { success: false, text: "Password must be at least 8 characters." };
    return;
  }

  processing.value = true;
  status.value = null;

  try {
    const response = await memberService.acceptInvite({
      token: onboardingForm.token,
      name: onboardingForm.name,
      password: onboardingForm.password,
      department: onboardingForm.department
    });
    
    status.value = { success: true, text: response.message };
    
    // Redirect to login after success
    setTimeout(() => {
      router.push({ name: 'login', query: { registered: 'true' } });
    }, 2000);
    
  } catch (err) {
    status.value = { 
      success: false, 
      text: err.response?.data?.error || "Registration failed. Please try again." 
    };
  } finally {
    processing.value = false;
  }
};
</script>

<style scoped>
.glass-panel {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.shadow-glass {
  box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
}

.animate-fade-in {
  animation: fadeIn 0.8s ease-out forwards;
}

.animate-slide-up {
  animation: slideUp 0.6s ease-out forwards;
}

.animate-shake {
  animation: shake 0.5s cubic-bezier(.36,.07,.19,.97) both;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes shake {
  10%, 90% { transform: translate3d(-1px, 0, 0); }
  20%, 80% { transform: translate3d(2px, 0, 0); }
  30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
  40%, 60% { transform: translate3d(4px, 0, 0); }
}
</style>
