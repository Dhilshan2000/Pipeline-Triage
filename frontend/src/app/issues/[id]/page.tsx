"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { downloadIssuePdfReport } from "@/lib/pdfReport";

export default function IssueDetailPage() {
  const params = useParams();
  const router = useRouter();
  const issueId = params?.id as string;

  const [issue, setIssue] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [commentText, setCommentText] = useState("");
  const [activeTab, setActiveTab] = useState<"report" | "facts" | "log">("report");

  useEffect(() => {
    if (issueId) {
      fetchIssue();
    }
  }, [issueId]);

  const fetchIssue = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/api/issues/${issueId}`);
      if (res.ok) {
        const data = await res.json();
        setIssue(data);
      }
    } catch (e) {
      console.warn("Could not fetch issue, using fallback view");
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (newStatus: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(`${apiUrl}/api/issues/${issueId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: newStatus,
          user_email: "dhilshan@example.com",
          resolution_notes: newStatus === "Resolved" ? "Fixed by updating failing tests and config." : undefined
        })
      });
      fetchIssue();
    } catch (e) {
      console.error(e);
    }
  };

  const submitComment = async () => {
    if (!commentText.trim()) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(`${apiUrl}/api/issues/${issueId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_email: "dhilshan@example.com",
          user_name: "Ariwalagan Dhilshan",
          text: commentText
        })
      });
      setCommentText("");
      fetchIssue();
    } catch (e) {
      console.error(e);
    }
  };

  const downloadReport = () => {
    if (!issue) return;
    const rep = issue.report || {};
    const steps = (rep.fix_steps || [])
      .map((s: any, idx: number) => `${s.step_number || idx + 1}. ${s.instruction}${s.code_snippet ? `\n\`\`\`\n${s.code_snippet}\n\`\`\`` : ""}`)
      .join("\n\n");
    const md = `# Pipeline Triage Report: ${issue.title || issueId}

- **Issue ID:** ${issue.id || issueId}
- **Project:** ${issue.project || "N/A"} (${issue.platform || "N/A"})
- **Category:** ${issue.category || "N/A"} (${Math.round((issue.confidence || 0.95) * 100)}% via ${issue.classifier_source || "rules"})
- **Status:** ${issue.status || "Open"}
- **Assignee:** ${issue.assignee || "Unassigned"}
- **Kanvaro Task:** ${issue.kanvaro_task_id || "N/A"}
- **Effort Estimate:** ${rep.effort_estimate || "N/A"}

## Summary
${rep.summary || "N/A"}

## Root Cause
${rep.root_cause || "N/A"}

## Step-by-Step Fix
${steps || "No fix steps provided."}

## Sources
${(rep.sources || []).map((s: string) => `- ${s}`).join("\n") || "- N/A"}

## Masked Log Excerpt
\`\`\`
${issue.log_excerpt || "No log excerpt available."}
\`\`\`
`;
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `triage-report-${issue.id || issueId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return <div className="p-12 text-center text-slate-400">Loading issue details...</div>;
  }

  const report = issue?.report || {
    summary: "Build failed during testing stage.",
    root_cause: "Coverage fell below the trainee gate threshold of 80%.",
    effort_estimate: "20 minutes",
    fix_steps: [
      { step_number: 1, instruction: "Add unit tests to cover uncovered branch in auth handler." },
      { step_number: 2, instruction: "Run pytest --cov to verify coverage >= 80% locally." }
    ],
    sources: ["sonarqube/rules/trainee-gate.md"]
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link href="/issues" className="text-sm text-blue-400 hover:underline mb-4 inline-block">
        &larr; Back to all issues
      </Link>

      <div className="flex flex-col lg:flex-row items-start justify-between gap-6 mb-8 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
              {issue?.category || "Triage Category"}
            </span>
            <span className="text-xs text-slate-500 font-mono">
              Fingerprint: {issue?.fingerprint?.slice(0, 12)}...
            </span>
            {issue?.occurrence_count > 1 && (
              <span className="bg-amber-500/20 text-amber-300 text-xs px-2 py-0.5 rounded-full font-bold">
                Occurred {issue.occurrence_count} times
              </span>
            )}
          </div>
          <h1 className="text-2xl font-bold text-white">{issue?.title || "Build Failure Issue"}</h1>
          <p className="text-sm text-slate-400 mt-1">
            Assigned to: <strong className="text-slate-200">{issue?.assignee}</strong> | Confidence:{" "}
            <strong className="text-slate-200">{Math.round((issue?.confidence || 0.95) * 100)}%</strong> ({issue?.classifier_source || "rules"})
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => downloadIssuePdfReport(issue)}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition shadow-sm"
          >
            Download Report (.pdf)
          </button>
          <button
            onClick={() => updateStatus("In progress")}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            Mark In Progress
          </button>
          <button
            onClick={() => updateStatus("Resolved")}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-sm"
          >
            Resolve &amp; Learn
          </button>
          <button
            onClick={() => updateStatus("Won't fix")}
            className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-red-600/20 hover:bg-red-600/30 text-red-300 transition"
          >
            Won't Fix
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-4 border-b border-slate-800 mb-6">
        <button
          onClick={() => setActiveTab("report")}
          className={`pb-3 text-sm font-semibold border-b-2 transition ${
            activeTab === "report" ? "border-blue-500 text-blue-400" : "border-transparent text-slate-400 hover:text-white"
          }`}
        >
          Diagnosis &amp; Solution
        </button>
        <button
          onClick={() => setActiveTab("facts")}
          className={`pb-3 text-sm font-semibold border-b-2 transition ${
            activeTab === "facts" ? "border-blue-500 text-blue-400" : "border-transparent text-slate-400 hover:text-white"
          }`}
        >
          CI Facts &amp; SonarQube
        </button>
        <button
          onClick={() => setActiveTab("log")}
          className={`pb-3 text-sm font-semibold border-b-2 transition ${
            activeTab === "log" ? "border-blue-500 text-blue-400" : "border-transparent text-slate-400 hover:text-white"
          }`}
        >
          Masked Log Excerpt
        </button>
      </div>

      {activeTab === "report" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold text-white mb-2">Summary</h2>
              <p className="text-slate-300 text-sm leading-relaxed">{report.summary}</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold text-white mb-2">Root Cause Analysis</h2>
              <p className="text-slate-300 text-sm leading-relaxed">{report.root_cause}</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Step-by-Step Fix Instructions</h2>
              <div className="space-y-4">
                {(report.fix_steps || []).map((step: any, idx: number) => (
                  <div key={idx} className="flex gap-4">
                    <div className="h-6 w-6 rounded-full bg-blue-600/20 text-blue-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                      {step.step_number || idx + 1}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm text-slate-200">{step.instruction}</p>
                      {step.code_or_command && (
                        <pre className="mt-2 p-3 bg-slate-950 rounded-lg text-xs font-mono text-emerald-400 overflow-x-auto border border-slate-800">
                          {step.code_or_command}
                        </pre>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Triage Context</h3>
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-xs text-slate-500">Estimated Effort</dt>
                  <dd className="font-semibold text-white">{report.effort_estimate || "15-30 min"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Connected Task</dt>
                  <dd className="text-blue-400 font-mono text-xs">Kanvaro MCP: KAN-104</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">RAG Sources Cited</dt>
                  <dd className="text-xs text-slate-300 mt-1">
                    {(report.sources || []).map((s: string, i: number) => (
                      <span key={i} className="block text-slate-400 font-mono">{s}</span>
                    ))}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h3 className="text-sm font-semibold text-white mb-4">Discussion &amp; History</h3>
              <div className="space-y-3 mb-4 max-h-60 overflow-y-auto">
                {(issue?.comments || []).map((c: any, i: number) => (
                  <div key={i} className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-xs">
                    <div className="flex justify-between text-slate-400 mb-1">
                      <strong>{c.user_name}</strong>
                      <span>{new Date(c.created_at).toLocaleTimeString()}</span>
                    </div>
                    <p className="text-slate-300">{c.text}</p>
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                <textarea
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  placeholder="Leave a comment or resolution note..."
                  rows={2}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
                />
                <button
                  onClick={submitComment}
                  className="w-full py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold"
                >
                  Post Comment
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "facts" && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Platform Pipeline Facts</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-xs text-slate-500">Project</span>
              <p className="font-semibold text-white">{issue?.project}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500">Branch</span>
              <p className="font-semibold text-white">{issue?.branch}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500">Pipeline ID</span>
              <p className="font-semibold text-white">#{issue?.pipeline_id}</p>
            </div>
            <div>
              <span className="text-xs text-slate-500">Failed Job</span>
              <p className="font-semibold text-white">{issue?.job_name}</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === "log" && (
        <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-300 overflow-x-auto">
          <p className="text-xs text-slate-500 mb-2">Secrets masked with [MASKED_SECRET] · Trimmed to error section</p>
          <pre>{issue?.latest_event?.log_excerpt || "[No raw log excerpt recorded for this failure event]"}</pre>
        </div>
      )}
    </div>
  );
}
