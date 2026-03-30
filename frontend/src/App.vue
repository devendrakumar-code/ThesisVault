<template>
  <div class="min-h-screen flex flex-col font-sans text-slate-900">
    <Navbar v-if="shouldShowShell" />

    <div class="flex flex-1 overflow-hidden">
      <Sidebar v-if="shouldShowShell" />

      <main 
        class="flex-1 overflow-y-auto relative" 
        :class="{ 'p-6 lg:p-8': shouldShowShell }"
      >
        <div class="max-w-7xl mx-auto w-full animate-fade-in relative z-10">
          <router-view />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'; // Added computed
import { useAuthStore } from '@/stores/authStore';
import { useRoute } from 'vue-router';
import Navbar from '@/components/common/Navbar.vue';
import Sidebar from '@/components/common/Sidebar.vue';

const authStore = useAuthStore();
const route = useRoute();

// Use a computed property to handle the visibility logic cleanly
const shouldShowShell = computed(() => {
  return authStore.isAuthenticated && route.meta.public !== true;
});
</script>
