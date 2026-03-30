<template>
  <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
    <div class="mb-10 animate-fade-in flex flex-col md:flex-row md:items-end md:justify-between gap-4">
      <div>
        <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">Organization Control Center</h1>
        <p class="text-slate-500 mt-1 font-medium">Manage members, projects, and institutional access for <strong>{{ authStore.user?.organization_name || 'Organization' }}</strong></p>
      </div>
      <div class="flex items-center gap-3">
        <div class="px-4 py-2 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
          <span class="text-xs font-bold text-indigo-700 uppercase tracking-widest">Administrator Access</span>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-[1.4fr,1fr] gap-6 mb-8 animate-fade-in">
      <div class="glass-panel rounded-3xl p-6 border border-slate-200/60 shadow-glass bg-white/80">
        <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-5">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.24em] text-indigo-600">Subscription Status</p>
            <h2 class="mt-3 text-2xl font-extrabold text-slate-900">{{ currentPlanName }}</h2>
            <p class="mt-2 text-sm text-slate-500">Keep track of your active plan and upgrade whenever your organization needs more capacity.</p>
          </div>
          <button
            type="button"
            @click="upgradeOpen = !upgradeOpen"
            :disabled="subscriptionLoading || availablePlanOptions.length === 0"
            class="px-5 py-3 rounded-xl text-sm font-bold transition-all border disabled:opacity-60 disabled:cursor-not-allowed"
            :class="upgradeOpen ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-indigo-600 border-indigo-200 hover:border-indigo-400 hover:bg-indigo-50'"
          >
            {{ availablePlanOptions.length === 0 ? 'No Other Plans' : (upgradeOpen ? 'Hide Plan Options' : 'Change Subscription') }}
          </button>
        </div>

        <div v-if="subscriptionLoading" class="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div v-for="index in 3" :key="index" class="rounded-2xl border border-slate-200 bg-slate-50/80 p-5 animate-pulse min-h-[120px]">
            <div class="h-4 bg-slate-200 rounded w-1/2 mb-4"></div>
            <div class="h-8 bg-slate-200 rounded w-2/3 mb-2"></div>
            <div class="h-4 bg-slate-200 rounded w-3/4"></div>
          </div>
        </div>

        <div v-else class="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="rounded-2xl border border-indigo-100 bg-indigo-50/80 p-5">
            <p class="text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">Days Left</p>
            <p class="mt-3 text-3xl font-extrabold text-slate-900">{{ daysLeftValue }}</p>
            <p class="mt-2 text-sm text-slate-500">{{ daysLeftCaption }}</p>
          </div>
          <div class="rounded-2xl border border-slate-200 bg-white/90 p-5">
            <p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Billing Window</p>
            <p class="mt-3 text-2xl font-extrabold text-slate-900">{{ formattedEndDate }}</p>
            <p class="mt-2 text-sm text-slate-500">{{ subscriptionStatusLabel }}</p>
          </div>
          <div class="rounded-2xl border border-slate-200 bg-white/90 p-5">
            <p class="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Project Usage</p>
            <p class="mt-3 text-2xl font-extrabold text-slate-900">{{ projectUsageLabel }}</p>
            <p class="mt-2 text-sm" :class="subscription?.current_plan?.has_ai_feature ? 'text-emerald-600' : 'text-slate-500'">
              {{ subscription?.current_plan?.has_ai_feature ? 'AI review is included in your plan.' : 'AI review is not included in your current plan.' }}
            </p>
          </div>
        </div>

        <div v-if="upgradeOpen && availablePlanOptions.length > 0" class="mt-6 border-t border-slate-200/70 pt-6">
          <div class="flex items-center justify-between gap-4 mb-4">
            <div>
              <h3 class="text-lg font-bold text-slate-900">Change Plan Anytime</h3>
              <p class="text-sm text-slate-500">Switch to any other plan from the same panel, whether you want to upgrade capacity or downgrade your subscription.</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div
              v-for="plan in availablePlanOptions"
              :key="plan.id"
              class="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm"
            >
              <div class="flex items-start justify-between gap-4">
                <div>
                  <p class="text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">{{ plan.display_name || plan.name }}</p>
                  <p class="mt-3 text-2xl font-extrabold text-slate-900">{{ plan.max_active_projects }} projects</p>
                </div>
                <span class="inline-flex rounded-full bg-emerald-50 px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-emerald-700">
                  {{ plan.has_ai_feature ? 'AI Included' : 'Core Only' }}
                </span>
              </div>

              <ul class="mt-4 space-y-2 text-sm text-slate-600">
                <li v-for="feature in plan.feature_list" :key="feature" class="flex items-start gap-2">
                  <span class="mt-0.5 text-indigo-500">�</span>
                  <span>{{ feature }}</span>
                </li>
              </ul>

              <button
                type="button"
                @click="upgradePlan(plan.name)"
                :disabled="upgradingPlanName === plan.name"
                class="mt-5 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-bold text-white transition-all hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {{ upgradingPlanName === plan.name ? 'Upgrading...' : `Upgrade to ${plan.name}` }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="glass-panel rounded-3xl p-6 border border-slate-200/60 shadow-glass bg-gradient-to-br from-slate-900 to-slate-800 text-white">
        <p class="text-xs font-bold uppercase tracking-[0.24em] text-indigo-200">Current Access</p>
        <h3 class="mt-3 text-2xl font-extrabold">{{ currentPlanName }}</h3>
        <p class="mt-3 text-sm text-slate-300">Your organization is currently set up for {{ projectUsageNarrative }}</p>
        <div class="mt-6 flex flex-wrap gap-2">
          <span class="inline-flex rounded-full border border-white/10 bg-white/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em]">
            {{ subscription?.subscription_status || 'active' }}
          </span>
          <span class="inline-flex rounded-full border border-white/10 bg-white/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em]">
            {{ subscription?.current_plan?.has_ai_feature ? 'AI enabled' : 'AI disabled' }}
          </span>
        </div>
        <p class="mt-8 text-xs uppercase tracking-[0.18em] text-slate-400">Subscription ends</p>
        <p class="mt-2 text-lg font-bold">{{ formattedEndDate }}</p>
      </div>
    </div>

    <div v-if="status" :class="status.success ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'" class="mb-8 rounded-2xl border px-5 py-4 text-sm font-bold shadow-sm animate-fade-in">
      {{ status.text }}
    </div>

    <div class="flex items-center gap-1 bg-slate-100/50 p-1 rounded-2xl mb-8 w-fit border border-slate-200/60 overflow-x-auto max-w-full">
      <button 
        v-for="tab in tabs" 
        :key="tab.id"
        @click="activeTab = tab.id"
        :class="activeTab === tab.id ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'"
        class="whitespace-nowrap px-6 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 flex items-center gap-2"
      >
        <span>{{ tab.icon }}</span>
        {{ tab.label }}
      </button>
    </div>

    <div class="min-h-[500px]">
      <div v-if="activeTab === 'invites'" class="animate-fade-in">
        <div class="glass-panel p-8 sm:p-12 rounded-3xl relative overflow-hidden shadow-glass border-t border-white">
          <div class="absolute top-[-50%] right-[-10%] w-96 h-96 bg-gradient-to-br from-indigo-100 to-purple-100 rounded-full blur-3xl mix-blend-multiply opacity-50 pointer-events-none"></div>

          <div class="relative z-10 max-w-2xl mx-auto text-center">
            <div class="w-16 h-16 bg-white shadow-sm rounded-2xl flex items-center justify-center text-3xl mx-auto mb-6 border border-slate-100">🎓</div>
            <h3 class="text-2xl font-extrabold text-slate-900 mb-2">Invite New Faculty</h3>
            <p class="text-slate-500 font-medium mb-8">Ready to expand your academic team? Send a secure onboarding link to a new professor.</p>

            <form @submit.prevent="sendInvite" class="mt-10 space-y-6">
              <div class="flex flex-col sm:flex-row items-center gap-4 justify-center">
                <div class="w-full sm:flex-1 text-left">
                  <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Full Name</label>
                  <input v-model="inviteForm.name" type="text" required placeholder="Professor's Full Name" class="input-field" />
                </div>
                <div class="w-full sm:flex-1 text-left">
                  <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Email Address</label>
                  <input v-model="inviteForm.email" type="email" required placeholder="faculty@university.edu" class="input-field" />
                </div>
              </div>
              <button type="submit" :disabled="sending" class="btn-primary w-full sm:w-auto shadow-neon flex items-center justify-center gap-2 h-[48px] px-10">
                <span v-if="sending" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                {{ sending ? 'Dispatching Invitation...' : 'Send Invitation' }}
              </button>
            </form>

            <div v-if="status" :class="status.success ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'" class="mt-8 p-4 rounded-xl text-sm font-bold border inline-block animate-fade-in shadow-sm">
              {{ status.text }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'faculty' || activeTab === 'students'" class="animate-fade-in">
        <div class="glass-panel rounded-3xl overflow-hidden shadow-glass border border-slate-200/60">
          <div class="p-6 border-b border-slate-100 bg-white/50 flex items-center justify-between">
            <h3 class="text-xl font-bold text-slate-900">Registered {{ activeTab === 'faculty' ? 'Professors' : 'Students' }}</h3>
            <div class="text-xs font-bold text-slate-400 uppercase tracking-widest">{{ members.length }} Total</div>
          </div>

          <div v-if="loading" class="py-20 flex flex-col items-center justify-center gap-4">
            <div class="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
            <p class="text-sm font-bold text-slate-400 uppercase tracking-widest">Loading Records...</p>
          </div>

          <div v-else-if="members.length === 0" class="py-20 px-6 text-center text-slate-500">
            <div class="text-4xl mb-4">{{ activeTab === 'faculty' ? '🎓' : '👤' }}</div>
            <p class="text-base font-semibold text-slate-700">
              There {{ activeTab === 'faculty' ? "aren't any professors yet." : "aren't any students yet." }}
            </p>
            <p class="mt-2 text-sm">Please try adding them.</p>
          </div>

          <div v-else class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/50 border-b border-slate-100">
                  <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Member</th>
                  <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Organization & Roles</th>
                  <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center">Status</th>
                  <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="member in members" :key="member.id" class="hover:bg-slate-50/50 transition-colors">
                  <td class="px-6 py-5">
                    <div class="flex items-center gap-3">
                      <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-50 to-indigo-100 flex items-center justify-center font-bold text-indigo-600 border border-indigo-200">
                        {{ member.name ? member.name.charAt(0) : '?' }}
                      </div>
                      <div>
                        <div class="font-bold text-slate-900 hover:text-indigo-600 cursor-pointer transition-colors">{{ member.name }}</div>
                        <div class="text-xs text-slate-400 font-medium">{{ member.email }}</div>
                      </div>
                    </div>
                  </td>
                  <td class="px-6 py-5">
                    <div class="flex flex-wrap gap-1.5">
                      <span v-for="role in member.roles" :key="role.name" class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 text-[10px] font-bold uppercase tracking-wider border border-slate-200">
                        {{ role.name }}
                      </span>
                    </div>
                  </td>
                  <td class="px-6 py-5 text-center">
                    <span :class="member.active ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : 'bg-rose-50 text-rose-700 ring-rose-200'" class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ring-1 ring-inset inline-block min-w-[90px]">
                      {{ member.active ? 'Active' : 'Locked' }}
                    </span>
                  </td>
                  <td class="px-6 py-5 text-right">
                    <button
                      v-if="member.id !== authStore.user?.id"
                      @click="toggleUserStatus(member)"
                      :class="member.active ? 'text-rose-600 hover:bg-rose-50' : 'text-emerald-600 hover:bg-emerald-50'"
                      class="px-4 py-1.5 rounded-lg text-xs font-bold transition-all border border-transparent hover:border-current inline-flex items-center gap-2"
                    >
                      <span v-if="member.active">🛑 Deactivate</span>
                      <span v-else>✅ Activate</span>
                    </button>
                    <span v-else class="text-[10px] font-bold text-slate-300 uppercase tracking-widest italic">Current User</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'projects'" class="animate-fade-in">
        <div class="glass-panel rounded-3xl overflow-hidden shadow-glass border border-slate-200/60">
          <div class="p-6 border-b border-slate-100 bg-white/50 flex items-center justify-between">
            <h3 class="text-xl font-bold text-slate-900">Institutional Projects</h3>
            <div class="text-xs font-bold text-slate-400 uppercase tracking-widest">{{ projects.length }} Total</div>
          </div>

          <div v-if="loading" class="py-20 flex flex-col items-center justify-center gap-4">
            <div class="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
            <p class="text-sm font-bold text-slate-400 uppercase tracking-widest">Loading Projects...</p>
          </div>

          <div v-else-if="projects.length === 0" class="py-20 px-6 text-center text-slate-500">
            <div class="text-4xl mb-4">📁</div>
            <p class="text-base font-semibold text-slate-700">There aren't any projects yet.</p>
            <p class="mt-2 text-sm">Create a project to get started.</p>
          </div>

          <div v-else class="overflow-x-auto">
            <table class="w-full text-left">
              <thead>
                <tr class="bg-slate-50/50 border-b border-slate-100">
                  <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest">Project Details</th>
                  <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center">Join Code</th>
                  <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-center">Status</th>
                  <th class="px-6 py-4 text-xs font-bold text-slate-500 uppercase tracking-widest text-right">Control</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="project in projects" :key="project.id" class="hover:bg-slate-50/50 transition-colors">
                  <td class="px-6 py-5 font-bold text-slate-900 group">
                    <div class="flex flex-col">
                      <span>{{ project.name }}</span>
                      <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">ID: {{ project.id.split('-')[0] }}...</span>
                    </div>
                  </td>
                  <td class="px-6 py-5 text-center">
                    <div class="flex items-center justify-center">
                      <code class="px-2.5 py-1 bg-indigo-50 rounded-lg text-indigo-700 font-mono text-xs font-black border border-indigo-100">
                        {{ project.join_code }}
                      </code>
                    </div>
                  </td>
                  <td class="px-6 py-5 text-center">
                    <span :class="project.status === 'active' ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : 'bg-slate-100 text-slate-500 ring-slate-200'" class="px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ring-1 ring-inset inline-block min-w-[90px]">
                      {{ project.status }}
                    </span>
                  </td>
                  <td class="px-6 py-5 text-right">
                    <button
                      @click="toggleProjectStatus(project)"
                      :class="project.status === 'active' ? 'text-rose-600 hover:bg-rose-50' : 'text-emerald-600 hover:bg-emerald-50'"
                      class="px-4 py-1.5 rounded-lg text-xs font-bold transition-all border border-transparent hover:border-current inline-flex items-center gap-2"
                    >
                      <span v-if="project.status === 'active'">🔒 Shut Down</span>
                      <span v-else>🔓 Reactivate</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, onMounted, watch } from 'vue';
import { useAuthStore } from '@/stores/authStore';
import { adminService } from '@/services/adminService';

const authStore = useAuthStore();
const activeTab = ref('invites');
const loading = ref(false);
const sending = ref(false);
const status = ref(null);
const subscriptionLoading = ref(false);
const upgradeOpen = ref(false);
const upgradingPlanName = ref('');
const subscription = ref(null);
const availablePlans = ref([]);

const tabs = [
  { id: 'invites', label: 'Invitations', icon: '📩' },
  { id: 'faculty', label: 'Faculty', icon: '🎓' },
  { id: 'students', label: 'Students', icon: '👤' },
  { id: 'projects', label: 'Projects', icon: '📁' }
];

const inviteForm = reactive({
  name: '',
  email: ''
});

const members = ref([]);
const projects = ref([]);

const currentPlanName = computed(() => subscription.value?.current_plan?.display_name || subscription.value?.current_plan?.name || 'No Plan');
const getPlanActionLabel = (plan) => {
  const currentRank = subscription.value?.current_plan?.rank ?? 99;
  const targetRank = plan?.rank ?? 99;
  if (targetRank > currentRank) return `Upgrade to ${plan.name}`;
  if (targetRank < currentRank) return `Downgrade to ${plan.name}`;
  return `Switch to ${plan.name}`;
};
const availablePlanOptions = computed(() => {
  const currentPlanId = subscription.value?.current_plan?.id;
  return availablePlans.value.filter((plan) => plan.id !== currentPlanId);
});
const daysLeftValue = computed(() => {
  if (!subscription.value) return '...';
  if (subscription.value.days_left === null || subscription.value.days_left === undefined) {
    return subscription.value.has_active_subscription ? 'Ongoing' : 'Expired';
  }
  return String(subscription.value.days_left);
});
const daysLeftCaption = computed(() => {
  if (!subscription.value) return 'Checking subscription details...';
  if (subscription.value.days_left === null || subscription.value.days_left === undefined) {
    return subscription.value.has_active_subscription
      ? 'This subscription is active without a scheduled expiry date.'
      : 'This subscription does not currently have an active billing window.';
  }
  return subscription.value.days_left === 1 ? 'day remaining on the current subscription' : 'days remaining on the current subscription';
});
const formattedEndDate = computed(() => {
  const raw = subscription.value?.subscription_ends_at;
  if (!raw) {
    return subscription.value?.has_active_subscription ? 'No expiry' : 'No active billing window';
  }
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) {
    return subscription.value?.has_active_subscription ? 'No expiry' : 'No active billing window';
  }
  return new Intl.DateTimeFormat('en-US', { year: 'numeric', month: 'short', day: 'numeric' }).format(date);
});
const subscriptionStatusLabel = computed(() => {
  const statusValue = subscription.value?.subscription_status;
  if (!statusValue) return 'Subscription status unavailable';
  const normalized = statusValue.charAt(0).toUpperCase() + statusValue.slice(1);
  return subscription.value?.has_active_subscription
    ? `Status: ${normalized}`
    : `Status: ${normalized} (attention needed)`;
});
const projectUsageLabel = computed(() => {
  const used = subscription.value?.active_projects ?? 0;
  const limit = subscription.value?.current_plan?.max_active_projects ?? 0;
  return `${used} / ${limit}`;
});
const projectUsageNarrative = computed(() => {
  const used = subscription.value?.active_projects ?? 0;
  const limit = subscription.value?.current_plan?.max_active_projects ?? 0;
  return `${used} active projects out of ${limit} available slots.`;
});

watch(activeTab, (newTab) => {
  if (newTab === 'faculty') fetchMembers('professor');
  else if (newTab === 'students') fetchMembers('student');
  else if (newTab === 'projects') fetchProjects();
});

onMounted(() => {
  if (activeTab.value === 'faculty') fetchMembers('professor');
  fetchSubscriptionState();
});

const fetchSubscriptionState = async () => {
  subscriptionLoading.value = true;
  try {
    const [summary, plans] = await Promise.all([
      adminService.getSubscriptionSummary(),
      adminService.getAvailablePlans()
    ]);
    subscription.value = summary;
    availablePlans.value = plans;
  } catch (err) {
    console.error('Failed to fetch subscription state', err);
    status.value = { success: false, text: err.response?.data?.error || 'Unable to load subscription details right now.' };
  } finally {
    subscriptionLoading.value = false;
  }
};

const fetchMembers = async (role) => {
  loading.value = true;
  try {
    members.value = await adminService.getMembers(role);
  } catch (err) {
    console.error('Failed to fetch members', err);
  } finally {
    loading.value = false;
  }
};

const fetchProjects = async () => {
  loading.value = true;
  try {
    projects.value = await adminService.getProjects();
  } catch (err) {
    console.error('Failed to fetch projects', err);
  } finally {
    loading.value = false;
  }
};

const sendInvite = async () => {
  sending.value = true;
  status.value = null;
  try {
    await adminService.inviteProfessor(inviteForm);
    status.value = { success: true, text: 'Invitation queued successfully' };
    inviteForm.name = '';
    inviteForm.email = '';
  } catch (err) {
    status.value = { success: false, text: err.response?.data?.error || 'Failed to dispatch invitation. Please check your network.' };
  } finally {
    sending.value = false;
  }
};

const upgradePlan = async (planName) => {
  upgradingPlanName.value = planName;
  status.value = null;
  try {
    const response = await adminService.changePlan(planName);
    if (response.subscription) {
      subscription.value = response.subscription;
    } else {
      await fetchSubscriptionState();
    }
    upgradeOpen.value = false;
    status.value = { success: true, text: response.message || `Subscription upgraded to ${planName}.` };
  } catch (err) {
    status.value = { success: false, text: err.response?.data?.error || 'Unable to upgrade the subscription right now.' };
  } finally {
    upgradingPlanName.value = '';
  }
};

const toggleUserStatus = async (user) => {
  const nextAction = user.active ? 'DEACTIVATE' : 'ACTIVATE';
  const confirmMsg = `SECURITY ALERT: Are you sure you want to ${nextAction} account for ${user.name}? They will lose all access immediately.`;

  if (!confirm(confirmMsg)) return;

  try {
    await adminService.toggleUserStatus(user.id);
    user.active = !user.active;
  } catch (err) {
    alert(err.response?.data?.error || 'System error: Unable to change user status.');
  }
};

const toggleProjectStatus = async (project) => {
  const newStatus = project.status === 'active' ? 'archived' : 'active';
  const actionText = newStatus === 'archived' ? 'SHUT DOWN' : 'REACTIVATE';
  const confirmMsg = `PROJECT CONTROL: Are you sure you want to ${actionText} "${project.name}"? Enrollment and new submissions will be blocked.`;

  if (!confirm(confirmMsg)) return;

  try {
    await adminService.toggleProjectStatus(project.id, newStatus);
    project.status = newStatus;
  } catch (err) {
    alert(err.response?.data?.error || 'System error: Unable to modify project status.');
  }
};
</script>

<style scoped>
.shadow-neon {
  box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.39);
}

.animate-fade-in {
  animation: fadeIn 0.4s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>






