<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
    <!-- Header Strategy: Trust & Transparency -->
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-black text-slate-900 tracking-tight">Subscription & Plan</h1>
        <p class="text-slate-500 font-medium">Manage your organization's capacity and view audit history.</p>
      </div>
      <div v-if="orgPlan" :class="[
        'px-4 py-2 rounded-full font-bold text-sm border shadow-sm flex items-center gap-2',
        orgPlan.name === 'Pro' ? 'bg-indigo-50 border-indigo-100 text-indigo-700' : 
        orgPlan.name === 'Enterprise' ? 'bg-emerald-50 border-emerald-100 text-emerald-700' : 'bg-slate-50 border-slate-200 text-slate-600'
      ]">
        <span class="relative flex h-2 w-2">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" :class="orgPlan.name === 'Pro' ? 'bg-indigo-400' : 'bg-slate-400'"></span>
          <span class="relative inline-flex rounded-full h-2 w-2" :class="orgPlan.name === 'Pro' ? 'bg-indigo-500' : 'bg-slate-500'"></span>
        </span>
        {{ orgPlan.name }} Subscription
      </div>
    </div>

    <!-- Usage Meters (Requirement 4: Measurable Limits) -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div v-for="limit in limits" :key="limit.label" class="glass-panel p-6 space-y-4 hover:shadow-md transition-shadow duration-300">
        <div class="flex justify-between items-center text-sm">
          <span class="font-bold text-slate-700 uppercase tracking-wider text-xs">{{ limit.label }}</span>
          <span class="font-black" :class="limit.percent > 90 ? 'text-rose-500' : 'text-slate-900'">{{ limit.current }} / {{ limit.max }}</span>
        </div>
        <div class="h-3 w-full bg-slate-100 rounded-full overflow-hidden shadow-inner">
          <div :class="['h-full rounded-full transition-all duration-1000 ease-out', limit.percent > 90 ? 'bg-rose-500' : limit.color]" :style="{ width: `${limit.percent}%` }"></div>
        </div>
        <p class="text-xs font-semibold" :class="limit.percent > 90 ? 'text-rose-600' : 'text-slate-400'">
          {{ limit.percent > 90 ? 'Limit nearly reached!' : limit.description }}
        </p>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Plan Options (Requirement: Data-driven plan management) -->
      <div class="lg:col-span-1 space-y-6">
        <h2 class="text-lg font-bold text-slate-900 flex items-center gap-2">
          <span class="p-1 rounded bg-indigo-500 text-white"><i class="fas fa-layer-group"></i></span>
          Available Plans
        </h2>
        <div class="space-y-4">
          <div v-for="p in allPlans" :key="p.id" 
               :class="['p-5 rounded-2xl border-2 transition-all duration-300 cursor-pointer relative overflow-hidden', 
                        orgPlan?.id === p.id ? 'border-indigo-500 bg-indigo-50/30' : 'border-slate-100 bg-white hover:border-slate-300 shadow-sm']"
               @click="handleSelectPlan(p)">
            <div v-if="orgPlan?.id === p.id" class="absolute -right-6 -top-6 w-12 h-12 bg-indigo-500 rotate-45 flex items-end justify-center pb-1">
              <i class="fas fa-check text-[10px] text-white"></i>
            </div>
            <div class="flex justify-between items-start mb-2">
              <span class="font-black text-slate-800">{{ p.name }}</span>
              <span class="text-xs font-bold text-indigo-500 lowercase">{{ p.validity }} days</span>
            </div>
            <ul class="text-xs font-semibold text-slate-500 space-y-2">
              <li class="flex items-center gap-2"><i class="fas fa-check text-indigo-400"></i> {{ p.max_active_projects }} Max Projects</li>
              <li class="flex items-center gap-2"><i class="fas fa-check text-indigo-400"></i> {{ p.max_students }} Max Students</li>
              <li class="flex items-center gap-2"><i class="fas fa-check text-indigo-400"></i> {{ p.monthly_ai_limit }} AI Evaluations</li>
              <li v-if="p.features && p.features.ai_analysis" class="flex items-center gap-2"><i class="fas fa-sparkles text-amber-400"></i> Advanced AI Reports</li>
            </ul>
            <button v-if="orgPlan?.id !== p.id" 
                    @click.stop="upgradePlan(p.name)"
                    class="mt-4 w-full py-2 rounded-xl bg-slate-900 text-white text-xs font-bold hover:bg-indigo-600 transition-colors shadow-sm">
              Upgrade to {{ p.name }}
            </button>
          </div>
        </div>

        <!-- Demonstration Control (Requirement: Lifecycle demo) -->
        <div class="glass-panel p-5 bg-amber-50/50 border-amber-100 mt-8 space-y-4">
          <h3 class="text-xs font-black text-amber-800 uppercase tracking-widest">Demo Control Center</h3>
          <p class="text-xs font-medium text-amber-700">Use these to simulate lifecycle states during your presentation.</p>
          <div class="flex gap-2">
            <button @click="toggleStatus" 
                    :class="['flex-1 py-2 rounded-lg text-xs font-bold transition-all shadow-sm', 
                             isSuspended ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white hover:bg-rose-700']">
              {{ isSuspended ? 'Resume Organization' : 'Suspend Organization' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Audit History (Requirement: Traceability & History modeling) -->
      <div class="lg:col-span-2 space-y-6">
        <h2 class="text-lg font-bold text-slate-900 flex items-center gap-2">
          <span class="p-1 rounded bg-slate-800 text-white"><i class="fas fa-history"></i></span>
          Compliance Audit History
        </h2>
        <div class="glass-panel overflow-hidden border-slate-100 shadow-sm">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50/50 border-b border-slate-100">
                  <th class="px-6 py-4 text-xs font-black text-slate-400 uppercase tracking-widest">Event</th>
                  <th class="px-6 py-4 text-xs font-black text-slate-400 uppercase tracking-widest">Details</th>
                  <th class="px-6 py-4 text-xs font-black text-slate-400 uppercase tracking-widest">Date</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50">
                <tr v-for="record in auditTrail" :key="record.id" class="hover:bg-slate-50/30 transition-colors group">
                  <td class="px-6 py-4">
                    <div class="flex items-center gap-3">
                      <span :class="[
                        'w-8 h-8 rounded-lg flex items-center justify-center text-xs shadow-sm',
                        record.new_plan ? 'bg-indigo-50 text-indigo-600' : 'bg-slate-50 text-slate-600'
                      ]">
                        <i :class="record.new_plan ? 'fas fa-arrow-up' : 'fas fa-bolt'"></i>
                      </span>
                      <span class="font-bold text-slate-900">{{ record.new_plan ? 'Plan Upgrade' : record.action }}</span>
                    </div>
                  </td>
                  <td class="px-6 py-4">
                    <p v-if="record.new_plan" class="text-sm font-medium text-slate-600 uppercase tracking-tighter">
                      {{ record.old_plan }} <i class="fas fa-long-arrow-right mx-1 text-slate-300"></i> <span class="font-black text-indigo-600">{{ record.new_plan }}</span>
                    </p>
                    <p v-else class="text-sm font-medium text-slate-500">{{ record.description }}</p>
                    <p class="text-[10px] text-slate-400 mt-0.5">{{ record.reason || `By ${record.user || 'System'}` }}</p>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-xs font-bold text-slate-400 group-hover:text-slate-600 transition-colors">
                    {{ formatDate(record.date) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!auditTrail.length" class="p-12 text-center space-y-2">
            <i class="fas fa-clipboard-list text-3xl text-slate-200"></i>
            <p class="text-slate-400 font-bold">No history available yet.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { adminService } from '@/services/adminService';
import { useAuthStore } from '@/stores/authStore';

const authStore = useAuthStore();
const orgPlan = computed(() => authStore.user?.organization?.plan);
const isSuspended = computed(() => authStore.user?.organization?.status === 'suspended');

const allPlans = ref([]);
const auditTrail = ref([]);
const orgUsage = ref(null);

const limits = computed(() => {
  if (!orgPlan.value || !authStore.user?.organization) return [];
  const org = authStore.user.organization;
  const p = orgPlan.value;

  return [
    { 
      label: 'Active Projects', 
      current: org.active_projects || 0, 
      max: p.max_active_projects, 
      percent: ((org.active_projects || 0) / p.max_active_projects) * 100,
      color: 'bg-indigo-500',
      description: 'Ongoing research projects.'
    },
    { 
      label: 'Student Capacity', 
      current: org.active_students || 0, 
      max: p.max_students, 
      percent: ((org.active_students || 0) / p.max_students) * 100,
      color: 'bg-blue-500',
      description: 'Maximum permitted researchers.'
    },
    { 
      label: 'Monthly AI Audit', 
      current: org.monthly_ai_count || 0, 
      max: p.monthly_ai_limit, 
      percent: ((org.monthly_ai_count || 0) / p.monthly_ai_limit) * 100,
      color: 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.3)]',
      description: 'AI-assisted thesis evaluations.'
    }
  ];
});

const loadData = async () => {
  try {
    const plansPromise = adminService.getPlans();
    const historyPromise = adminService.getHistory();
    const [plans, history] = await Promise.all([plansPromise, historyPromise]);
    
    allPlans.value = plans;
    
    // Merge subscription_history and activity_logs into one sorted audit trail
    const combined = [
      ...history.subscription_history,
      ...history.activity_logs
    ].sort((a, b) => new Date(b.date) - new Date(a.date));
    
    auditTrail.value = combined;
  } catch (err) {
    console.error("Failed to load subscription data", err);
  }
};

const upgradePlan = async (name) => {
  try {
    await adminService.upgradePlan(name);
    // Silent Refresh user in session
    const updatedUser = { ...authStore.user };
    // This is a simplified demo update. In real app, re-fetch user profile from backend.
    window.location.reload(); 
  } catch (err) {
    alert("Upgrade failed: " + (err.response?.data?.message || err.message));
  }
};

const toggleStatus = async () => {
  try {
    if (isSuspended.value) {
      await adminService.resumeOrg();
    } else {
      await adminService.suspendOrg();
    }
    window.location.reload();
  } catch (err) {
    alert("Operation failed: " + (err.response?.data?.message || err.message));
  }
};

const formatDate = (dateStr) => {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
};

onMounted(loadData);
</script>

<style scoped>
.glass-panel {
  @apply bg-white border border-slate-100 rounded-3xl shadow-sm backdrop-blur-md bg-opacity-80;
}
</style>
