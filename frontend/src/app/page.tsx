export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 text-center">
      <div className="max-w-2xl bg-slate-800 border border-slate-700 rounded-xl p-8 shadow-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 mb-4">
          Pipeline Triage System
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white mb-3">
          Automated CI/CD Build Failure Triage
        </h1>
        <p className="text-slate-300 text-sm mb-6">
          Watches GitLab and GitHub pipelines. Pinpoints failure root causes using rules and grounded LLM reports, routes to responsible engineers, prevents duplicate issue noise, and detects recurring patterns.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-left">
          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-700/50">
            <span className="text-xs text-slate-400">CI Adapters</span>
            <p className="text-sm font-medium text-emerald-400">GitLab & GitHub</p>
          </div>
          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-700/50">
            <span className="text-xs text-slate-400">Classification</span>
            <p className="text-sm font-medium text-blue-400">Rules + LLM</p>
          </div>
          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-700/50">
            <span className="text-xs text-slate-400">Task Sync</span>
            <p className="text-sm font-medium text-purple-400">Kanvaro (MCP)</p>
          </div>
          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-700/50">
            <span className="text-xs text-slate-400">Deduplication</span>
            <p className="text-sm font-medium text-amber-400">Fingerprint Merge</p>
          </div>
        </div>
      </div>
    </main>
  );
}
