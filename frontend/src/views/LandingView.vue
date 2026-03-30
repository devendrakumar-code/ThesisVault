<template>
  <div class="min-h-screen bg-slate-50 relative overflow-hidden flex flex-col items-center">
    <!-- Decorative background elements -->
    <div class="absolute top-[-10%] left-[-10%] w-96 h-96 bg-indigo-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
    <div class="absolute top-[20%] right-[-10%] w-96 h-96 bg-blue-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
    <div class="absolute bottom-[-10%] left-[20%] w-96 h-96 bg-purple-400 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>

    <div class="relative z-10 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-32 flex flex-col items-center text-center">
      <div class="inline-flex items-center px-4 py-2 rounded-full glass-panel mb-8 animate-fade-in shadow-sm">
        <span class="w-2 h-2 rounded-full bg-indigo-500 mr-2 animate-pulse"></span>
        <span class="text-sm font-semibold text-indigo-800 tracking-wide uppercase">Powered by Gemini 1.5 Pro</span>
      </div>
      
      <h1 class="text-5xl md:text-7xl font-extrabold tracking-tight text-slate-900 mb-6 animate-slide-up">
        Secure Academic Integrity with <br />
        <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 via-blue-600 to-purple-600">ThesisVault</span>
      </h1>
      
      <p class="mt-4 max-w-2xl text-lg md:text-xl text-slate-600 mb-10 animate-fade-in animation-delay-500">
        The ultimate AI-powered platform tailored for universities to manage, evaluate, and effortlessly verify student theses.
      </p>
      
      <div class="flex flex-col sm:flex-row gap-4 animate-slide-up animation-delay-500">
        <router-link to="/login" class="btn-primary flex items-center gap-2 group">
          Sign In
          <span class="group-hover:translate-x-1 transition-transform">→</span>
        </router-link>
        <router-link to="/register-org" class="btn-secondary">
          Register Institution
        </router-link>
      </div>
    </div>

    <!-- Feature Cards -->
    <div class="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 relative z-10 mt-[-2rem]">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        
        <div class="glass-card p-8 rounded-2xl animate-fade-in text-left">
          <div class="w-14 h-14 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-600 text-3xl mb-6 shadow-sm">
            🏢
          </div>
          <h3 class="text-2xl font-bold text-slate-900 mb-3">For Administrators</h3>
          <p class="text-slate-600 leading-relaxed text-sm">
            Manage institutional access seamlessly. Invite faculty members, configure academic periods, and control your organization's subscription plans.
          </p>
        </div>

        <div class="glass-card p-8 rounded-2xl animate-fade-in animation-delay-200 text-left">
          <div class="w-14 h-14 rounded-xl bg-blue-100 flex items-center justify-center text-blue-600 text-3xl mb-6 shadow-sm">
            📚
          </div>
          <h3 class="text-2xl font-bold text-slate-900 mb-3">For Professors</h3>
          <p class="text-slate-600 leading-relaxed text-sm">
            Create structured research projects, generate unique join codes, and effortlessly view AI-enhanced feedback on student thesis submissions.
          </p>
        </div>

        <div class="glass-card p-8 rounded-2xl animate-fade-in animation-delay-400 relative overflow-hidden group text-left">
          <div class="w-14 h-14 rounded-xl bg-purple-100 flex items-center justify-center text-purple-600 text-3xl mb-6 shadow-sm">
            🎓
          </div>
          <h3 class="text-2xl font-bold text-slate-900 mb-3">For Students</h3>
          <p class="text-slate-600 leading-relaxed text-sm mb-6">
            Join projects instantly using simple codes. Submit research and receive detailed, constructive AI analysis on your work methodology.
          </p>
          <router-link to="/student-join" class="inline-flex items-center text-sm font-bold text-indigo-600 hover:text-indigo-800 transition-colors">
            Join a Project as Student <span class="ml-1 group-hover:translate-x-1 transition-transform">→</span>
          </router-link>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.animation-delay-200 { animation-delay: 200ms; }
.animation-delay-400 { animation-delay: 400ms; }
.animation-delay-500 { animation-delay: 500ms; }
.animation-delay-2000 { animation-delay: 2s; }
.animation-delay-4000 { animation-delay: 4s; }
.animate-blob {
  animation: blob 7s infinite;
}
@keyframes blob {
  0% { transform: translate(0px, 0px) scale(1); }
  33% { transform: translate(30px, -50px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
  100% { transform: translate(0px, 0px) scale(1); }
}
</style>
