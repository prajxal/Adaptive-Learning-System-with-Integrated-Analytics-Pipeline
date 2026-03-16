import React, { useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, Outlet, useLocation } from 'react-router-dom';
import { SignedIn, SignedOut, useAuth } from '@clerk/clerk-react';
import { AppNavbar } from './components/AppNavbar';
import { AppSidebar } from './components/AppSidebar';
import { Login } from './pages/Login';
import { Signup } from './pages/Signup';
import { LandingPage } from './pages/LandingPage';
import CourseDetailPage from './pages/CourseDetailPage';
import RoadmapCatalogPage from './pages/RoadmapCatalogPage';
import RoadmapDetailPage from './pages/RoadmapDetailPage';
import DashboardPage from './pages/DashboardPage';
import ResourceViewerPage from './pages/ResourceViewerPage';
import MyProgressPage from './pages/MyProgressPage';
import QuizPage from './pages/QuizPage';

import { useEffect as UseEffectAlias } from 'react';

function AppLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const location = useLocation();
  console.log("[AppLayout] Rendering at location:", location.pathname);

  let currentPage = 'roadmap';
  if (location.pathname.startsWith('/dashboard')) currentPage = 'dashboard';
  else if (location.pathname.startsWith('/profile')) currentPage = 'profile';
  else if (location.pathname.startsWith('/progress')) currentPage = 'progress';

  return (
    <div className="flex h-screen overflow-hidden bg-[#0a0a0f]">
      <AppSidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        currentPage={currentPage}
      />

      <div className="flex flex-col flex-1 overflow-hidden">
        <AppNavbar onMenuClick={() => setIsSidebarOpen(true)} showMenuButton={true} />
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/signin" element={<Login />} />
        <Route path="/login" element={<Navigate to="/signin" replace />} />
        <Route path="/signup" element={<Signup />} />

        <Route element={
          <>
            <SignedIn>
              <AppLayout />
            </SignedIn>
            <SignedOut>
              <Navigate to="/signin" replace />
            </SignedOut>
          </>
        }>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/roadmaps" element={<RoadmapCatalogPage />} />
            <Route path="/roadmap/:roadmapId" element={<RoadmapDetailPage />} />
            <Route path="/course/:courseId" element={<CourseDetailPage />} />
            <Route path="/course/:courseId/resource/:resourceId" element={<ResourceViewerPage />} />
            <Route path="/course/:courseId/quiz" element={<QuizPage />} />
            <Route path="/progress" element={<MyProgressPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
