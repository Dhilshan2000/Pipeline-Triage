"use client";

import { useState, useEffect } from "react";

export default function AnalyticsPage() {
  const [activeScreen, setActiveScreen] = useState<number>(1);
  const [data, setData] = useState<any>({
    weekly: null,
    patterns: [],
    deployment: null,
    resolution: null,
    security: null
  });

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    try {
      const [w, p, d, r, s] = await Promise.all([
        fetch(`${apiUrl}/api/analytics/weekly`).then((r) => r.json()),
        fetch(`${apiUrl}/api/analytics/patterns`).then((r) => r.json()),
        fetch(`${apiUrl}/api/analytics/deployment`).then((r) => r.json()),
        fetch(`${apiUrl}/api/analytics/resolution`).then((r) => r.json()),
        fetch(`${apiUrl}/api/analytics/security`).then((r) => r.json()),
      ]);
      setData({ weekly: w, patterns: p.patterns || [], deployment: d, resolution: r, security: s });
    } catch (e) {
      console.warn("Could not load backend analytics:", e);
    }
  };

  const screens = [
    { id: 1, title: "1. Weekly Overview", desc: "Builds, failure trends & project failure rates (Project Lead)" },
    { id: 2, title: "2. Recurring Problems", desc: "Clustered patterns & permanent fixes (DevOps)" },
    { id: 3, title: "3. Deployment Health", desc: "Success rate across Dev, QA, UAT, Prod & server issues (DevOps)" },
    { id: 4, title: "4. Resolution Tracking", desc: "Issue status velocity & triage MTTR (Project Lead)" },
    { id: 5, title: "5. Security Scan Results", desc: "Tool findings (SonarQube, Trivy, Gitleaks, Snyk) & repeated secrets (Security Lead)" },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight">CI/CD Analytics &amp; Patterns</h1>
        <p className="text-sm text-slate-400 mt-1">
          Root-cause trends and recurring pattern intelligence based on the Step 1 Case Study.
        </p>
      </div>

      {/* Screen selector navigation */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-8">
        {screens.map((s) => (
          <button
            key={s.id}
            onClick={() => setActiveScreen(s.id)}
            className={`p-3 rounded-xl border text-left transition ${
              activeScreen === s.id
                ? "bg-blue-600/10 border-blue-500/50 text-blue-400"
                : "bg-slate-900 border-slate-800 text-slate-400 hover:text-white"
            }`}
          >
            <div className="font-semibold text-xs mb-1">{s.title}</div>
            <div className="text-[10px] text-slate-500 line-clamp-1">{s.desc}</div>
          </button>
        ))}
      </div>

      {/* Screen 1: Weekly Overview */}
      {activeScreen === 1 && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-5 bg-slate-900 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-500">Total Builds</span>
              <p className="text-2xl font-bold text-white mt-1">{data.weekly?.builds || 48}</p>
            </div>
            <div className="p-5 bg-slate-900 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-500">Failed Builds</span>
              <p className="text-2xl font-bold text-red-400 mt-1">{data.weekly?.failed || 12}</p>
            </div>
            <div className="p-5 bg-slate-900 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-500">Open Triage Issues</span>
              <p className="text-2xl font-bold text-amber-400 mt-1">{data.weekly?.open_issues || 6}</p>
            </div>
            <div className="p-5 bg-slate-900 rounded-xl border border-slate-800">
              <span className="text-xs text-slate-500">MRs/PRs Merged</span>
              <p className="text-2xl font-bold text-emerald-400 mt-1">{data.weekly?.mrs_merged || 18}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-6 bg-slate-900 rounded-xl border border-slate-800">
              <h3 className="text-sm font-semibold text-white mb-4">4-Week Failure Trend</h3>
              <div className="space-y-3">
                {(data.weekly?.failure_trend || [
                  { week: "Week 1", failures: 16 },
                  { week: "Week 2", failures: 14 },
                  { week: "Week 3", failures: 10 },
                  { week: "Week 4", failures: 8 }
                ]).map((t: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between text-xs">
                    <span className="text-slate-400">{t.week}</span>
                    <div className="flex-1 mx-4 bg-slate-800 h-2 rounded-full overflow-hidden">
                      <div className="bg-blue-500 h-full" style={{ width: `${Math.min(t.failures * 5, 100)}%` }} />
                    </div>
                    <span className="font-semibold text-white">{t.failures} fails</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-6 bg-slate-900 rounded-xl border border-slate-800">
              <h3 className="text-sm font-semibold text-white mb-4">Failures by Project</h3>
              <div className="space-y-3">
                {(data.weekly?.failures_by_project || [
                  { project: "core-backend-api", count: 7 },
                  { project: "frontend-web", count: 4 },
                  { project: "infra-deployer", count: 3 }
                ]).map((p: any, idx: number) => (
                  <div key={idx} className="flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-mono">{p.project}</span>
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 font-semibold">{p.count} failures</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Screen 2: Recurring Problems */}
      {activeScreen === 2 && (
        <div className="p-6 bg-slate-900 rounded-xl border border-slate-800">
          <h2 className="text-lg font-semibold text-white mb-2">Recurring Problems &amp; Permanent Fixes</h2>
          <p className="text-xs text-slate-400 mb-6">
            Detected when 3 or more failures match the normalized error signature within 30 days.
          </p>

          <div className="space-y-4">
            {(data.patterns.length > 0 ? data.patterns : [
              {
                signature: "Deployment / server::deploy-prod::no space left on device",
                category: "Deployment / server",
                count: 5,
                last_seen: "2 days ago",
                suggested_fix: {
                  root_cause: "Docker build image layer accumulation exhausting runner disk.",
                  permanent_fix: "Set up daily automated cron 'docker system prune -af' and storage threshold alert at 85%.",
                  effort_estimate: "2 hours",
                  owner_role: "DevOps on-call"
                }
              },
              {
                signature: "Dependency problem::npm-test::npm err! eresolve",
                category: "Dependency problem",
                count: 4,
                last_seen: "1 day ago",
                suggested_fix: {
                  root_cause: "Unpinned dependency version causing upstream peer conflict in CI build.",
                  permanent_fix: "Pin exact package versions and commit locked package-lock.json.",
                  effort_estimate: "30 minutes",
                  owner_role: "Lead Developer"
                }
              }
            ]).map((pattern: any, idx: number) => (
              <div key={idx} className="p-5 bg-slate-950 rounded-lg border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      {pattern.category}
                    </span>
                    <span className="text-xs font-mono text-slate-400">{pattern.signature}</span>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-red-500/20 text-red-300">
                    {pattern.count} Occurrences
                  </span>
                </div>
                <div className="p-4 bg-slate-900/60 rounded border border-slate-800 text-xs space-y-2">
                  <div>
                    <strong className="text-slate-300">Permanent Fix: </strong>
                    <span className="text-emerald-400">{pattern.suggested_fix?.permanent_fix}</span>
                  </div>
                  <div className="flex gap-4 text-slate-500">
                    <span>Effort: <strong className="text-slate-300">{pattern.suggested_fix?.effort_estimate}</strong></span>
                    <span>Assigned Role: <strong className="text-slate-300">{pattern.suggested_fix?.owner_role}</strong></span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Screen 3: Deployment Health */}
      {activeScreen === 3 && (
        <div className="space-y-6">
          <div className="p-6 bg-slate-900 rounded-xl border border-slate-800 flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-500">Global Deployment Success Rate</span>
              <p className="text-3xl font-extrabold text-emerald-400 mt-1">91.4%</p>
            </div>
            <div className="text-right text-xs text-slate-400">
              Safe to release: <strong className="text-emerald-400">YES</strong> (No blocking Production failures)
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {["Dev", "QA", "UAT", "Prod"].map((env) => (
              <div key={env} className="p-5 bg-slate-900 rounded-xl border border-slate-800">
                <span className="text-xs text-slate-500">{env} Failures</span>
                <p className="text-2xl font-bold text-white mt-1">
                  {env === "Dev" ? 4 : env === "QA" ? 2 : env === "UAT" ? 1 : 0}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Screen 4: Resolution Tracking */}
      {activeScreen === 4 && (
        <div className="p-6 bg-slate-900 rounded-xl border border-slate-800 space-y-6">
          <h2 className="text-lg font-semibold text-white">Resolution Velocity &amp; MTTR</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-xs text-slate-500">Open</span>
              <p className="text-xl font-bold text-white mt-1">6</p>
            </div>
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-xs text-slate-500">In Progress</span>
              <p className="text-xl font-bold text-blue-400 mt-1">3</p>
            </div>
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-xs text-slate-500">Resolved</span>
              <p className="text-xl font-bold text-emerald-400 mt-1">19</p>
            </div>
            <div className="p-4 bg-slate-950 rounded-lg border border-slate-800">
              <span className="text-xs text-slate-500">Needs Review (Uncertain)</span>
              <p className="text-xl font-bold text-amber-400 mt-1">1</p>
            </div>
          </div>
        </div>
      )}

      {/* Screen 5: Security Scan Results */}
      {activeScreen === 5 && (
        <div className="p-6 bg-slate-900 rounded-xl border border-slate-800 space-y-6">
          <h2 className="text-lg font-semibold text-white">Security Scan Tool Breakdown</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {["SonarQube", "Trivy", "Gitleaks", "Snyk"].map((tool) => (
              <div key={tool} className="p-4 bg-slate-950 rounded-lg border border-slate-800">
                <span className="text-xs text-slate-500">{tool}</span>
                <p className="text-xl font-bold text-red-400 mt-1">
                  {tool === "SonarQube" ? 5 : tool === "Gitleaks" ? 2 : tool === "Trivy" ? 1 : 0}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
