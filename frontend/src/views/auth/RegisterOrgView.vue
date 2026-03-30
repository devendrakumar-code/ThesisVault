<template>
  <div class="min-h-screen bg-slate-50 relative overflow-hidden flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="absolute top-[10%] right-[-10%] w-[500px] h-[500px] bg-indigo-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>

    <div class="sm:mx-auto sm:w-full sm:max-w-md relative z-10 text-center mb-6 animate-fade-in">
      <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 shadow-md flex items-center justify-center mx-auto mb-4">
        <span class="text-white font-bold text-2xl">T</span>
      </div>
      <h2 class="text-3xl font-extrabold text-slate-900 tracking-tight">Register Institution</h2>
      <p class="mt-2 text-sm text-slate-600">
        Already have an account?
        <router-link to="/login" class="font-bold text-indigo-600 hover:text-indigo-500 transition-colors">Sign in</router-link>
      </p>
    </div>

    <div class="mt-2 sm:mx-auto sm:w-full sm:max-w-5xl relative z-10 animate-slide-up animation-delay-200">
      <div class="glass-panel py-8 px-4 sm:rounded-2xl sm:px-10 shadow-glass">
        <form @submit.prevent="handleRegistration" class="space-y-6">
          <div class="grid grid-cols-1 gap-6">
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">Institution Name</label>
              <input v-model="form.organization.name" type="text" required class="input-field" placeholder="e.g. IIT Madras" />
            </div>
          </div>

          <div class="border-t border-slate-200/60 my-6"></div>

          <div class="space-y-5">
            <h3 class="text-lg font-bold text-slate-900 bg-clip-text text-transparent bg-gradient-to-r from-indigo-700 to-blue-600">Admin Account</h3>
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">Full Name</label>
              <input v-model="form.owner.name" type="text" required class="input-field" placeholder="Admin Name" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">Email Address</label>
              <input v-model="form.owner.email" type="email" required class="input-field" placeholder="admin@domain.edu" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-slate-700 mb-1">Password</label>
              <input v-model="form.owner.password" type="password" required class="input-field" placeholder="Password" />
            </div>
          </div>

          <div class="pt-2 space-y-4">
            <div class="flex flex-col gap-1">
              <label class="block text-sm font-semibold text-slate-700">Choose Your Plan</label>
              <p class="text-sm text-slate-500">Select the organization plan that matches your project capacity and AI review needs.</p>
            </div>

            <div v-if="plansLoading" class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div v-for="index in 3" :key="index" class="rounded-2xl border border-slate-200 bg-white/70 p-5 animate-pulse min-h-[220px]">
                <div class="h-5 bg-slate-200 rounded w-1/2 mb-4"></div>
                <div class="h-8 bg-slate-200 rounded w-2/3 mb-5"></div>
                <div class="space-y-3">
                  <div class="h-4 bg-slate-200 rounded"></div>
                  <div class="h-4 bg-slate-200 rounded w-5/6"></div>
                  <div class="h-4 bg-slate-200 rounded w-2/3"></div>
                </div>
              </div>
            </div>

            <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button
                v-for="plan in plans"
                :key="plan.id"
                type="button"
                :tabindex="0"
                @click="selectPlan(plan.name)"
                @keydown.enter.prevent="selectPlan(plan.name)"
                @keydown.space.prevent="selectPlan(plan.name)"
                :aria-pressed="form.plan_name === plan.name"
                :class="form.plan_name === plan.name
                  ? 'border-indigo-500 ring-2 ring-indigo-200 bg-indigo-50/80 shadow-lg shadow-indigo-100/80'
                  : 'border-slate-200 bg-white/80 hover:border-indigo-300 hover:bg-white'"
                class="text-left rounded-2xl border p-5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-300 min-h-[220px] flex flex-col"
              >
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">{{ getPlanEyebrow(plan) }}</p>
                    <h4 class="mt-2 text-xl font-extrabold text-slate-900">{{ plan.display_name || plan.name }}</h4>
                  </div>
                  <span
                    :class="form.plan_name === plan.name ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-400'"
                    class="mt-1 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-black"
                  >
                    {{ form.plan_name === plan.name ? '*' : '' }}
                  </span>
                </div>

                <div class="mt-5">
                  <p class="text-3xl font-extrabold text-slate-900">{{ formatProjectLimit(plan.max_active_projects) }}</p>
                  <p class="text-sm text-slate-500 mt-1">active project capacity</p>
                </div>

                <ul class="mt-5 space-y-3 text-sm text-slate-600">
                  <li
                    v-for="feature in plan.feature_list"
                    :key="feature"
                    class="flex items-start gap-2"
                  >
                    <span class="mt-0.5 text-indigo-500">•</span>
                    <span>{{ feature }}</span>
                  </li>
                </ul>

                <p class="mt-auto pt-5 text-xs font-semibold uppercase tracking-[0.18em]" :class="plan.has_ai_feature ? 'text-emerald-600' : 'text-slate-400'">
                  {{ plan.has_ai_feature ? 'AI-enabled workflow' : 'Core workflow only' }}
                </p>
              </button>
            </div>
          </div>

          <div v-if="error" class="text-red-600 text-sm font-medium bg-red-50/80 backdrop-blur-sm p-3 rounded-lg border border-red-100">
            {{ error }}
          </div>

          <button type="submit" :disabled="loading || plansLoading || !form.plan_name" class="btn-primary w-full shadow-neon mt-4 disabled:opacity-60 disabled:cursor-not-allowed">
            <span v-if="loading" class="flex items-center gap-2">
              <svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              Processing...
            </span>
            <span v-else>Complete Registration</span>
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { authService } from '@/services/authService';

const router = useRouter();
const loading = ref(false);
const plansLoading = ref(false);
const error = ref(null);
const plans = ref([]);

const form = reactive({
  organization: {
    name: ''
  },
  owner: {
    name: '',
    email: '',
    password: ''
  },
  plan_name: ''
});

const getPlanEyebrow = (plan) => {
  if (!plan?.name) return 'Plan';
  const name = plan.name.toLowerCase();
  if (name === 'free') return 'Starter tier';
  if (name === 'pro') return 'Growth tier';
  if (name === 'enterprise') return 'Scale tier';
  return 'Plan';
};

const formatProjectLimit = (value) => {
  const count = Number(value) || 0;
  return `${count} project${count === 1 ? '' : 's'}`;
};

const selectPlan = (planName) => {
  form.plan_name = planName;
};

onMounted(async () => {
  plansLoading.value = true;
  error.value = null;

  try {
    plans.value = await authService.getPlans();
    if (plans.value.length > 0) {
      form.plan_name = plans.value[0].name;
    }
  } catch (err) {
    console.error('Failed to load plans', err);
    error.value = 'Error fetching plans: ' + (err.response?.data?.error || err.message);
  } finally {
    plansLoading.value = false;
  }
});

const handleRegistration = async () => {
  loading.value = true;
  error.value = null;

  try {
    await authService.registerOrg(form);
    router.push({ name: 'login', query: { registered: 'true' } });
  } catch (err) {
    if (err.response && err.response.data && err.response.data.errors) {
      error.value = 'Validation Error: ' + JSON.stringify(err.response.data.errors);
    } else {
      error.value = err.response?.data?.error || err.message || 'An unknown error occurred.';
    }
  } finally {
    loading.value = false;
  }
};
</script>

