<template>
  <div class="max-w-4xl mx-auto py-10 px-4 sm:px-6 lg:px-8">
    <div class="mb-8 animate-fade-in">
      <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">Profile Settings</h1>
      <p class="text-slate-500 mt-1 font-medium">Manage your personal information and academic details.</p>
    </div>

    <div class="glass-panel p-8 sm:p-10 rounded-3xl relative overflow-hidden animate-slide-up shadow-glass border-t border-white">
      <div class="absolute top-[-20%] left-[-10%] w-64 h-64 bg-indigo-100/50 rounded-full blur-3xl mix-blend-multiply pointer-events-none"></div>
      
      <div class="relative z-10">
        <div class="flex items-center gap-6 mb-10">
          <div 
            @click="triggerFileSelect"
            class="w-24 h-24 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-4xl text-white font-bold shadow-neon border-4 border-white cursor-pointer group relative overflow-hidden"
            title="Click to change photo"
          >
            <img v-if="imagePreview || authStore.user?.profile_image" :src="imagePreview || getFullImageUrl(authStore.user.profile_image)" class="w-full h-full object-cover" />
            <span v-else>{{ form.name ? form.name.charAt(0).toUpperCase() : '👤' }}</span>
            <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-xs font-bold text-white">
              CHANGE
            </div>
            <input type="file" ref="fileInput" class="hidden" accept="image/*" @change="handleFileChange" />
          </div>
          <div>
            <h2 class="text-2xl font-bold text-slate-900">{{ form.name || 'Your Profile' }}</h2>
            <p class="text-slate-500 font-medium">Update your photo and personal details.</p>
          </div>
        </div>

        <form @submit.prevent="saveProfile" class="space-y-8">
          <div class="grid grid-cols-1 gap-y-6 gap-x-6 sm:grid-cols-6 border-b border-slate-100 pb-8">
            <div class="sm:col-span-4">
              <label class="block text-sm font-bold text-slate-700 mb-2">Full Name</label>
              <input v-model="form.name" type="text" class="input-field shadow-sm bg-white" placeholder="John Doe" />
            </div>

            <div class="sm:col-span-4">
              <label class="block text-sm font-bold text-slate-700 mb-2">Email Address</label>
              <div class="relative">
                <input :value="userEmail" disabled type="email" class="input-field shadow-inner bg-slate-50 text-slate-500 cursor-not-allowed border-slate-200" />
                <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                  <span class="text-slate-400">🔒</span>
                </div>
              </div>
              <p class="mt-2 text-xs font-semibold text-slate-400 flex items-center gap-1"><span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span> Email verified and locked for security.</p>
            </div>
            
            <div class="sm:col-span-6"><hr class="border-slate-100 my-2"></div>

            <div v-if="authStore.isProfessor" class="sm:col-span-4 animate-fade-in">
              <label class="block text-sm font-bold text-slate-700 mb-2">Department</label>
              <input v-model="form.department" type="text" placeholder="e.g. Computer Science" class="input-field shadow-sm bg-white" />
            </div>

            <template v-if="authStore.isStudent">
              <div class="sm:col-span-4 animate-fade-in">
                <label class="block text-sm font-bold text-slate-700 mb-2">Major</label>
                <input v-model="form.major" type="text" class="input-field shadow-sm bg-white" placeholder="e.g. Software Engineering" />
              </div>
              <div class="sm:col-span-2 animate-fade-in">
                <label class="block text-sm font-bold text-slate-700 mb-2">Semester</label>
                <input v-model.number="form.semester" type="number" min="1" class="input-field shadow-sm bg-white text-center font-bold" />
              </div>
            </template>
          </div>

          <div v-if="message" :class="message.type === 'success' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'" class="p-4 rounded-xl text-sm font-bold border inline-block animate-fade-in shadow-sm w-full">
            <span class="mr-2">{{ message.type === 'success' ? '✅' : '⚠️' }}</span> {{ message.text }}
          </div>

          <div class="flex justify-end pt-4">
            <button type="submit" :disabled="saving" class="btn-primary shadow-neon px-8 flex items-center gap-2">
              <span v-if="saving" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
              {{ saving ? 'Saving Preferences...' : 'Save Changes' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useAuthStore } from '@/stores/authStore';
import { profileService } from '@/services/profileService';

const authStore = useAuthStore();
const userEmail = ref('');
const saving = ref(false);
const message = ref(null);

const form = reactive({
  name: '',
  department: '',
  major: '',
  semester: 1
});

const fileInput = ref(null);
const selectedFile = ref(null);
const imagePreview = ref(null);

const getFullImageUrl = (path) => {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
  const normalizedPath = path.startsWith('/') ? path.slice(1) : path;
  return `${baseUrl}/${normalizedPath}`;
};

const triggerFileSelect = () => fileInput.value?.click();

const handleFileChange = (e) => {
  const file = e.target.files[0];
  if (file) {
    selectedFile.value = file;
    imagePreview.value = URL.createObjectURL(file);
  }
};

const loadProfile = async () => {
  try {
    const res = await profileService.getMyProfile();
    const data = res.data;
    
    form.name = data.name;
    userEmail.value = data.email;
    
    if (authStore.isProfessor) {
      form.department = data.details?.department || '';
    } else if (authStore.isStudent) {
      form.major = data.details?.major || '';
      form.semester = data.details?.semester || 1;
    }
  } catch (err) {
    console.error("Failed to load profile", err);
  }
};

const saveProfile = async () => {
  saving.value = true;
  message.value = null;
  try {
    const formData = new FormData();
    formData.append('name', form.name);
    if (authStore.isProfessor) formData.append('department', form.department);
    if (authStore.isStudent) {
      formData.append('major', form.major);
      formData.append('semester', form.semester);
    }
    if (selectedFile.value) {
      formData.append('image', selectedFile.value);
    }

    const updated = await profileService.updateProfile(formData);
    
    // Update the local authStore user data
    // Assuming backend returns { success: true, message: ..., data: { ...user... } }
    if (updated && updated.data) {
      authStore.user = updated.data;
      sessionStorage.setItem('user', JSON.stringify(updated.data));
    }
    
    message.value = { type: 'success', text: 'Profile updated successfully!' };
    
    // Clear temporary preview
    selectedFile.value = null;
    imagePreview.value = null;
  } catch (err) {
    message.value = { type: 'error', text: err.response?.data?.message || 'Update failed' };
  } finally {
    saving.value = false;
  }
};

onMounted(loadProfile);
</script>
