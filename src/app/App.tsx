import React, { useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, Outlet, useLocation } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
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
import QuizPage from './pages/QuizPage';
import MyProfilePage from './pages/MyProfilePage';
import AIMentorPage from './pages/AIMentorPage';

import { useEffect as UseEffectAlias } from 'react';

function AppLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const location = useLocation();
  console.log("[AppLayout] Rendering at location:", location.pathname);

  let currentPage = 'roadmap';
  if (location.pathname.startsWith('/dashboard')) currentPage = 'dashboard';
  else if (location.pathname.startsWith('/ai-mentor')) currentPage = 'ai-mentor';
  else if (location.pathname.startsWith('/profile')) currentPage = 'profile';

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
              <ErrorBoundary>
                <AppLayout />
              </ErrorBoundary>
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
            <Route path="/ai-mentor" element={<AIMentorPage />} />
            <Route path="/profile" element={<MyProfilePage />} />
            <Route path="/progress" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
