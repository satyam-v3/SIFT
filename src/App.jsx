import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ReportsProvider } from './context/ReportsContext';
import { AppShell } from './components/layout/AppShell';

import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Reports } from './pages/Reports';
import { ReportDetails } from './pages/ReportDetails';
import { AnalyzeReport } from './pages/AnalyzeReport';
import { Intelligence } from './pages/Intelligence';
import { LifeSavingRules } from './pages/LifeSavingRules';
import { LifeSavingRuleDetails } from './pages/LifeSavingRuleDetails';
import { ReviewQueue } from './pages/ReviewQueue';
import { Actions } from './pages/Actions';
import { Facilities } from './pages/Facilities';
import { FacilityDetails } from './pages/FacilityDetails';
import { Settings } from './pages/Settings';
import { AnnotationWorkbench } from './pages/AnnotationWorkbench';
import { AnnotationAdjudication } from './pages/AnnotationAdjudication';

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ReportsProvider>
          <Routes>
            {/* Public Auth Route */}
            <Route path="/login" element={<Login />} />

            {/* Authenticated Layout Shell */}
            <Route element={<AppShell />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/reports/:id" element={<ReportDetails />} />
              <Route path="/analyze" element={<AnalyzeReport />} />
              <Route path="/intelligence" element={<Intelligence />} />
              <Route path="/life-saving-rules" element={<LifeSavingRules />} />
              <Route path="/life-saving-rules/:id" element={<LifeSavingRuleDetails />} />
              <Route path="/review" element={<ReviewQueue />} />
              <Route path="/actions" element={<Actions />} />
              <Route path="/facilities" element={<Facilities />} />
              <Route path="/facilities/:id" element={<FacilityDetails />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/annotations" element={<AnnotationWorkbench />} />
              <Route path="/annotations/adjudication" element={<AnnotationAdjudication />} />
            </Route>

            {/* Catch-all fallback */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </ReportsProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
