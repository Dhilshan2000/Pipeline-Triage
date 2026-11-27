"use client";

import { useState, useEffect } from "react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<"adapters" | "connectors" | "rules" | "users">("adapters");
  const [connectors, setConnectors] = useState<any[]>([]);
  const [connName, setConnName] = useState("slack");
  const [connType, setConnType] = useState("rest");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [apiToken, setApiToken] = useState("");
  const [saveMsg, setSaveMsg] = useState("");

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchConnectors = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/settings/connectors`);
      if (res.ok) {
        const data = await res.json();
        setConnectors(data.connectors || []);
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchConnectors();
  }, []);

  const handleAddConnector = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveMsg("");
    try {
      const res = await fetch(`${apiUrl}/api/settings/connectors`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: connType,
          name: connName,
          enabled: true,
          config: {
            webhook_url: webhookUrl,
            api_token: apiToken,
          },
        }),
      });
      if (res.ok) {
        setSaveMsg(`Saved '${connName}' connector with Fernet-encrypted credentials!`);
        setWebhookUrl("");
        setApiToken("");
        fetchConnectors();
      }
    } catch {
      setSaveMsg("Failed to save connector.");
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight">System Settings</h1>
        <p className="text-sm text-slate-400 mt-1">
          Manage pluggable CI adapters, output connectors with Fernet encrypted credentials, and routing rules.
        </p>
      </div>

      <div className="flex items-center gap-4 border-b border-slate-800 mb-6">
        {[
          { id: "adapters", label: "CI Adapters (Input)" },
          { id: "connectors", label: "Connectors (Output)" },
          { id: "rules", label: "Classification & Routing Rules" },
          { id: "users", label: "Users & Git Email Map" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`pb-3 text-sm font-semibold border-b-2 transition ${
              activeTab === tab.id ? "border-blue-500 text-blue-400" : "border-transparent text-slate-400 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "adapters" && (
        <div className="space-y-4">
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-white">GitLab CI Adapter</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Active</span>
              </div>
              <p className="text-xs text-slate-400 mt-1">Webhook URL: /api/webhooks/gitlab · Secret: [Encrypted with Fernet]</p>
            </div>
            <button className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-xs font-semibold">Configure</button>
          </div>

          <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-white">GitHub Actions Adapter</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Active</span>
              </div>
              <p className="text-xs text-slate-400 mt-1">Webhook URL: /api/webhooks/github · Signature: HMAC-SHA256</p>
            </div>
            <button className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-xs font-semibold">Configure</button>
          </div>

          <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-white">Bitbucket Pipelines Adapter</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">Registered (Pluggable)</span>
              </div>
              <p className="text-xs text-slate-400 mt-1">Webhook URL: /api/webhooks/bitbucket · Signature: X-Hub-Signature (HMAC-SHA256)</p>
            </div>
            <button className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-xs font-semibold">Configure</button>
          </div>
        </div>
      )}

      {activeTab === "connectors" && (
        <div className="space-y-4">
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-white">Kanvaro Task Tool (MCP)</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">Connected</span>
              </div>
              <p className="text-xs text-slate-400 mt-1">Server: http://mock-kanvaro:8080 · Bot User: triage-bot · Session Renew: ~7 days</p>
            </div>
            <button className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-xs font-semibold">Test Ping</button>
          </div>

          <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-white">Email / Mailpit (SMTP)</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">Ready</span>
              </div>
              <p className="text-xs text-slate-400 mt-1">Host: mailpit:1025 · Delivery SLA: &lt; 2 minutes</p>
            </div>
            <button className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded-lg text-xs font-semibold">Send Test Email</button>
          </div>

          {connectors
            .filter((c) => !["kanvaro", "email"].includes(c.name))
            .map((c) => (
              <div key={c.name} className="p-5 bg-slate-900 border border-slate-800 rounded-xl flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-white capitalize">{c.name} Connector</h3>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      {c.enabled ? "Enabled" : "Disabled"} ({c.type.toUpperCase()})
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">Configured via Settings · Credentials encrypted with Fernet</p>
                </div>
                <span className="text-xs text-slate-500 font-mono">{c.type}</span>
              </div>
            ))}

          <form onSubmit={handleAddConnector} className="p-6 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-white">+ Add Output Connector (Slack / Jira / Custom REST)</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Plug in a new destination directly through Settings without editing core code.
              </p>
            </div>
            {saveMsg && (
              <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-400">
                {saveMsg}
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Connector Name</label>
                <select
                  value={connName}
                  onChange={(e) => setConnName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-sm text-white"
                >
                  <option value="slack">Slack (Incoming Webhook)</option>
                  <option value="jira">Jira (Cloud REST API)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Connector Type</label>
                <select
                  value={connType}
                  onChange={(e) => setConnType(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-sm text-white"
                >
                  <option value="rest">REST Connector</option>
                  <option value="mcp">MCP Connector</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">Webhook URL / Jira Base URL</label>
                <input
                  type="url"
                  required
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  placeholder="https://hooks.slack.com/services/..."
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-sm text-white"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">API Token / Secret (Optional for Slack Webhook)</label>
                <input
                  type="password"
                  value={apiToken}
                  onChange={(e) => setApiToken(e.target.value)}
                  placeholder="Optional Jira API token"
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-sm text-white"
                />
              </div>
            </div>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white transition"
            >
              Save Connector
            </button>
          </form>
        </div>
      )}

      {activeTab === "rules" && (
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl">
          <h3 className="text-base font-semibold text-white mb-2">Deterministic Classification &amp; Routing Rules</h3>
          <p className="text-xs text-slate-400 mb-4">
            Rules execute first with confidence &ge; 0.85 threshold. Prompts in commit messages cannot modify routing.
          </p>
          <div className="space-y-2 text-xs">
            <div className="p-3 bg-slate-950 rounded border border-slate-800 flex justify-between">
              <span className="text-slate-300 font-mono">Stage: sonarqube / Quality Gate &rarr; SonarQube quality gate</span>
              <span className="text-emerald-400">Routes to: Commit Author</span>
            </div>
            <div className="p-3 bg-slate-950 rounded border border-slate-800 flex justify-between">
              <span className="text-slate-300 font-mono">Stage: deploy / Error: No space left on device &rarr; Deployment / server</span>
              <span className="text-blue-400">Routes to: DevOps On-Call</span>
            </div>
            <div className="p-3 bg-slate-950 rounded border border-slate-800 flex justify-between">
              <span className="text-slate-300 font-mono">Job: gitleaks / trivy / snyk &rarr; Security scan</span>
              <span className="text-red-400">Routes to: Security Lead</span>
            </div>
          </div>
        </div>
      )}

      {activeTab === "users" && (
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl">
          <h3 className="text-base font-semibold text-white mb-4">Git Author Email &rarr; User Mapping</h3>
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-500">
                <th className="pb-2">Git Commit Email</th>
                <th className="pb-2">Mapped System User</th>
                <th className="pb-2">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              <tr>
                <td className="py-2.5 font-mono text-slate-300">dhilshan@example.com</td>
                <td className="py-2.5 text-white">Ariwalagan Dhilshan</td>
                <td className="py-2.5 text-purple-400">Developer</td>
              </tr>
              <tr>
                <td className="py-2.5 font-mono text-slate-300">devops-oncall@example.com</td>
                <td className="py-2.5 text-white">DevOps On-Call Rotation</td>
                <td className="py-2.5 text-blue-400">DevOps</td>
              </tr>
              <tr>
                <td className="py-2.5 font-mono text-slate-300">security-lead@example.com</td>
                <td className="py-2.5 text-white">SecOps Lead</td>
                <td className="py-2.5 text-red-400">Security</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
