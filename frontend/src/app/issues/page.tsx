"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { downloadIssuePdfReport } from "@/lib/pdfReport";

interface IssueItem {
  id: string;
  title: string;
  status: string;
  category: string;
  assignee: string;
  project: string;
  branch: string;
  occurrence_count: number;
  last_seen: string;
  report?: {
    summary?: string;
    effort_estimate?: string;
  };
}

export default function IssuesPage() {
  const [issues, setIssues] = useState<IssueItem[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>("All");
  const [search, setSearch] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchIssues();
  }, [filterStatus]);

  const fetchIssues = async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const statusParam = filterStatus !== "All" ? `?status=${encodeURIComponent(filterStatus)}` : "";
      const res = await fetch(`${apiUrl}/api/issues${statusParam}`);
      if (res.ok) {
        const data = await res.json();
        setIssues(data.issues || []);
      }
    } catch (e) {
      console.warn("Using sample mock data:", e);
      setIssues([
        {
          id: "issue_mock_1",
          title: "[SonarQube quality gate] sonarqube-check failed in core-backend-api",
          status: "Open",
          category: "SonarQube quality gate",
          assignee: "dhilshan@example.com",
          project: "core-backend-api",
          branch: "main",
          occurrence_count: 3,
          last_seen: new Date().toISOString(),
          report: {
            summary: "Quality gate failed: Coverage on new code is 71.4% (Threshold: 80.0%).",
            effort_estimate: "20 minutes"
          }
        },
        {
          id: "issue_mock_2",
          title: "[Deployment / server] deploy-prod failed in infra-deployer",
          status: "In progress",
          category: "Deployment / server",
          assignee: "devops-oncall@example.com",
          project: "infra-deployer",
          branch: "main",
          occurrence_count: 5,
          last_seen: new Date().toISOString(),
          report: {
            summary: "Disk space exhausted on target runner node ('No space left on device').",
            effort_estimate: "1 hour"
          }
        },
        {
          id: "issue_mock_3",
          title: "[Dependency problem] npm-test failed in frontend-web",
          status: "Open",
          category: "Dependency problem",
          assignee: "developer@example.com",
          project: "frontend-web",
          branch: "feature/auth",
          occurrence_count: 1,
          last_seen: new Date().toISOString(),
          report: {
            summary: "npm ERR! ERESOLVE could not resolve conflicting peer dependencies.",
            effort_estimate: "15 minutes"
          }
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const filtered = issues.filter(
    (i) =>
      i.title.toLowerCase().includes(search.toLowerCase()) ||
      i.project.toLowerCase().includes(search.toLowerCase())
  );

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case "SonarQube quality gate": return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      case "Security scan": return "bg-red-500/10 text-red-400 border-red-500/20";
      case "Deployment / server": return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "Docker registry": return "bg-orange-500/10 text-orange-400 border-orange-500/20";
      case "Dependency problem": return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      default: return "bg-slate-700/40 text-slate-300 border-slate-600";
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Active Triage Issues</h1>
          <p className="text-sm text-slate-400 mt-1">
            Grounded failure diagnosis, automatic routing, and deduplicated issue tracking.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {["All", "Open", "In progress", "Resolved", "Won't fix"].map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                filterStatus === status
                  ? "bg-blue-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <input
          type="text"
          placeholder="Search by project or issue title..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-slate-900 border border-slate-800 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
        />
      </div>

      <div className="space-y-3">
        {loading ? (
          <div className="p-12 text-center text-slate-400">Loading issues...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-400 bg-slate-900/50 rounded-xl border border-slate-800">
            No matching issues found.
          </div>
        ) : (
          filtered.map((issue) => (
            <div
              key={issue.id}
              className="bg-slate-900/70 hover:bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl p-5 transition shadow-sm"
            >
              <div className="flex items-start justify-between gap-4">
                <Link href={`/issues/${issue.id}`} className="flex-1 block">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getCategoryColor(issue.category)}`}>
                      {issue.category}
                    </span>
                    <span className="text-xs text-slate-500 font-mono">{issue.project} : {issue.branch}</span>
                    {issue.occurrence_count > 1 && (
                      <span className="bg-amber-500/20 text-amber-300 text-xs px-2 py-0.5 rounded-full font-bold">
                        Repeated {issue.occurrence_count}×
                      </span>
                    )}
                  </div>
                  <h3 className="text-base font-semibold text-white mb-1">{issue.title}</h3>
                  {issue.report?.summary && (
                    <p className="text-sm text-slate-300 line-clamp-1">{issue.report.summary}</p>
                  )}
                </Link>
                <div className="text-right shrink-0 flex flex-col items-end gap-2">
                  <span className={`inline-block px-2.5 py-1 rounded text-xs font-semibold ${
                    issue.status === "Resolved" ? "bg-emerald-500/20 text-emerald-400" :
                    issue.status === "In progress" ? "bg-blue-500/20 text-blue-400" :
                    "bg-slate-800 text-slate-300"
                  }`}>
                    {issue.status}
                  </span>
                  <p className="text-xs text-slate-400">Owner: {issue.assignee}</p>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      downloadIssuePdfReport(issue);
                    }}
                    className="px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition"
                  >
                    Download PDF
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
