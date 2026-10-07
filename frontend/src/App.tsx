import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
import { JobsList } from './components/JobsList';
import { JobDetail } from './components/JobDetail';
import { RemediationsList } from './components/RemediationsList';
import { EscalationsList } from './components/EscalationsList';
import { SimulatorModal } from './components/SimulatorModal';
import {
  fetchDashboardStats,
  fetchJobs,
  fetchJobDetail,
  fetchActivityFeed,
  fetchRemediations,
  fetchEscalations,
} from './services/api';
import { DashboardStats, JobRunSummary, JobRunDetail, ActivityItem, RemediationItem, EscalationItem } from './types/job';

export function App() {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [platform, setPlatform] = useState<'MOCK_SAP' | 'SAP_BTP'>('MOCK_SAP');
  const [stats, setStats] = useState<DashboardStats>({
    total_jobs: 0,
    failed_jobs: 0,
    successful_jobs: 0,
    running_jobs: 0,
    failure_rate: 0,
    success_rate: 0,
    agent_status: 'ONLINE',
    platform: 'MOCK_SAP',
  });
  const [jobs, setJobs] = useState<JobRunSummary[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [remediations, setRemediations] = useState<RemediationItem[]>([]);
  const [escalations, setEscalations] = useState<EscalationItem[]>([]);
  const [selectedJob, setSelectedJob] = useState<JobRunDetail | null>(null);
  const [isSimulatorOpen, setIsSimulatorOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = async (targetPlatform: 'MOCK_SAP' | 'SAP_BTP' = platform) => {
    try {
      const [statsData, jobsData, activityData, remediationsData, escalationsData] = await Promise.all([
        fetchDashboardStats(targetPlatform),
        fetchJobs(undefined, undefined, false, targetPlatform),
        fetchActivityFeed(targetPlatform),
        fetchRemediations(undefined, targetPlatform),
        fetchEscalations(targetPlatform),
      ]);
      setStats(statsData);
      setJobs(jobsData);
      setActivity(activityData);
      setRemediations(remediationsData);
      setEscalations(escalationsData);
    } catch (err) {
      console.error('Error loading operational data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePlatformChange = async (newPlatform: 'MOCK_SAP' | 'SAP_BTP') => {
    setPlatform(newPlatform);
    setSelectedJob(null);
    try {
      const { switchEnvironment } = await import('./services/api');
      await switchEnvironment(newPlatform);
    } catch (e) {
      console.warn('Switch notice:', e);
    }
    await loadData(newPlatform);
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => loadData(platform), 5000);
    return () => clearInterval(interval);
  }, [platform]);

  const handleSelectJob = async (jobName: string, runCount: number) => {
    try {
      const detail = await fetchJobDetail(jobName, runCount);
      setSelectedJob(detail);
    } catch (err) {
      console.error('Error fetching job details:', err);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-slate-100 flex flex-col">
      {/* Top Navigation Bar */}
      <Header
        onSearch={(term) => {
          if (term) setCurrentTab('all');
        }}
        onOpenSimulator={() => setIsSimulatorOpen(true)}
        agentStatus={stats.agent_status}
        platform={platform}
        onPlatformChange={handlePlatformChange}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Navigation Sidebar */}
        <Sidebar
          currentTab={currentTab}
          onTabChange={(tab) => {
            setCurrentTab(tab);
            setSelectedJob(null);
          }}
          failedCount={stats.failed_jobs}
          escalationsCount={escalations.length}
        />

        {/* Dynamic View Panel */}
        <main className="flex-1 overflow-y-auto p-6">
          {selectedJob ? (
            <JobDetail job={selectedJob} onBack={() => setSelectedJob(null)} />
          ) : currentTab === 'dashboard' ? (
            <Dashboard
              stats={stats}
              recentJobs={jobs.slice(0, 10)}
              activity={activity}
              onSelectJob={handleSelectJob}
            />
          ) : currentTab === 'all' ? (
            <JobsList jobs={jobs} onSelectJob={handleSelectJob} />
          ) : currentTab === 'failed' ? (
            <JobsList jobs={jobs} filterStatus="FAILED" onSelectJob={handleSelectJob} />
          ) : currentTab === 'remediations' ? (
            <RemediationsList remediations={remediations} onSelectJob={handleSelectJob} />
          ) : currentTab === 'escalations' ? (
            <EscalationsList escalations={escalations} onRefresh={loadData} onSelectJob={handleSelectJob} />
          ) : currentTab === 'success' ? (
            <JobsList jobs={jobs} filterStatus="SUCCESS" onSelectJob={handleSelectJob} />
          ) : (
            <Dashboard
              stats={stats}
              recentJobs={jobs}
              activity={activity}
              onSelectJob={handleSelectJob}
            />
          )}
        </main>
      </div>

      {/* Simulator Modal */}
      <SimulatorModal
        isOpen={isSimulatorOpen}
        onClose={() => setIsSimulatorOpen(false)}
        onRefresh={loadData}
      />
    </div>
  );
}
export default App;
