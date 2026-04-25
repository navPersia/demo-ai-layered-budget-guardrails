import React from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  CircleDollarSign,
  Save,
  Power,
  RefreshCcw,
  RotateCcw,
  Send,
  Settings2,
  Shield,
  User
} from "lucide-react";
import studioStreamXLogoUrl from "../studiostreamx_web_assets/svg/studiostreamx-logo-no-gap-white.svg";
import "./styles.css";

type Role = "user" | "assistant" | "system";

type Message = {
  id: string;
  role: Role;
  text: string;
};

type BudgetStatus = {
  workspaceId?: string;
  sessionId?: string;
  sessionEstimatedCostUsd?: number;
  requestEstimatedCostUsd?: number;
  dailyEstimatedCostUsd?: number;
  monthlyEstimatedCostUsd?: number;
  killSwitchEnabled?: boolean;
  sessionRequestCount?: number;
};

type StatusResponse = {
  workspace: {
    id: string;
    workspaceId: string;
    dailyBudgetUsd: number;
    monthlyBudgetUsd: number;
    sessionBudgetUsd: number;
    requestBudgetUsd: number;
    maxRequestsPerSession: number;
    maxOutputTokens: number;
  };
  killSwitch: {
    enabled: boolean;
    reason: string | null;
  };
  dailyEstimatedCostUsd: number;
  monthlyEstimatedCostUsd: number;
  cosmosMode: string;
};

type BudgetForm = {
  dailyBudgetUsd: string;
  monthlyBudgetUsd: string;
  sessionBudgetUsd: string;
  requestBudgetUsd: string;
  maxRequestsPerSession: string;
  maxOutputTokens: string;
};

const defaultApiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  "https://ca-func-ai-budget-api.salmoncliff-ac0e8a07.westeurope.azurecontainerapps.io";

function newSessionId() {
  return `ui-${crypto.randomUUID().slice(0, 8)}`;
}

function currency(value?: number) {
  return `$${Number(value || 0).toFixed(6)}`;
}

function defaultBudgetForm(): BudgetForm {
  return {
    dailyBudgetUsd: "5",
    monthlyBudgetUsd: "30",
    sessionBudgetUsd: "1",
    requestBudgetUsd: "0.05",
    maxRequestsPerSession: "20",
    maxOutputTokens: "500"
  };
}

function formFromStatus(data: StatusResponse): BudgetForm {
  return {
    dailyBudgetUsd: String(data.workspace.dailyBudgetUsd),
    monthlyBudgetUsd: String(data.workspace.monthlyBudgetUsd),
    sessionBudgetUsd: String(data.workspace.sessionBudgetUsd),
    requestBudgetUsd: String(data.workspace.requestBudgetUsd),
    maxRequestsPerSession: String(data.workspace.maxRequestsPerSession),
    maxOutputTokens: String(data.workspace.maxOutputTokens)
  };
}

function App() {
  const [apiBaseUrl, setApiBaseUrl] = React.useState(defaultApiBaseUrl);
  const [workspaceId, setWorkspaceId] = React.useState("demo-workspace");
  const [sessionId, setSessionId] = React.useState(newSessionId());
  const [adminApiKey, setAdminApiKey] = React.useState("");
  const [input, setInput] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [status, setStatus] = React.useState<StatusResponse | null>(null);
  const [budget, setBudget] = React.useState<BudgetStatus | null>(null);
  const [budgetForm, setBudgetForm] = React.useState<BudgetForm>(defaultBudgetForm());
  const [messages, setMessages] = React.useState<Message[]>([
    {
      id: "welcome",
      role: "system",
      text: "Ready."
    }
  ]);

  const normalizedApiBaseUrl = apiBaseUrl.replace(/\/$/, "");

  async function request<T>(
    path: string,
    init?: RequestInit,
    options?: { admin?: boolean }
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json"
    };
    if (options?.admin && adminApiKey.trim()) {
      headers["x-admin-api-key"] = adminApiKey.trim();
    }

    const response = await fetch(`${normalizedApiBaseUrl}${path}`, {
      ...init,
      headers: {
        ...headers,
        ...(init?.headers || {})
      }
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    if (!response.ok) {
      throw new Error(data.reason || data.error || `HTTP ${response.status}`);
    }
    return data as T;
  }

  async function refreshStatus() {
    const data = await request<StatusResponse>(
      `/api/status?workspaceId=${encodeURIComponent(workspaceId)}`,
      undefined,
      { admin: true }
    );
    setStatus(data);
    setBudgetForm(formFromStatus(data));
    setBudget((current) => ({
      ...current,
      workspaceId,
      dailyEstimatedCostUsd: data.dailyEstimatedCostUsd,
      monthlyEstimatedCostUsd: data.monthlyEstimatedCostUsd,
      killSwitchEnabled: data.killSwitch.enabled
    }));
  }

  async function sendMessage() {
    const text = input.trim();
    if (!text || busy) return;

    setBusy(true);
    setInput("");
    setMessages((items) => [...items, { id: crypto.randomUUID(), role: "user", text }]);

    try {
      const data = await request<{
        allowed: boolean;
        message?: string;
        reason?: string;
        warning?: string;
        budget?: BudgetStatus;
      }>("/api/chat", {
        method: "POST",
        body: JSON.stringify({ workspaceId, sessionId, message: text })
      }, { admin: true });

      setBudget(data.budget || null);
      setMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: data.allowed ? "assistant" : "system",
          text: data.allowed ? data.message || "" : data.reason || "Blocked."
        }
      ]);
      if (data.warning) {
        setMessages((items) => [
          ...items,
          { id: crypto.randomUUID(), role: "system", text: data.warning || "" }
        ]);
      }
      await refreshStatus();
    } catch (error) {
      setMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "system",
          text: error instanceof Error ? error.message : "Request failed."
        }
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function setKillSwitch(enabled: boolean) {
    setBusy(true);
    try {
      await request(`/api/kill-switch/${enabled ? "enable" : "disable"}`, {
        method: "POST",
        body: JSON.stringify({
          workspaceId,
          reason: enabled ? "Enabled from chat UI." : undefined
        })
      }, { admin: true });
      await refreshStatus();
    } finally {
      setBusy(false);
    }
  }

  async function resetDemo() {
    setBusy(true);
    try {
      await request("/api/budget/configure-demo", {
        method: "POST",
        body: JSON.stringify({ workspaceId, ...budgetPayload(defaultBudgetForm()) })
      }, { admin: true });
      await request("/api/budget/reset-demo", {
        method: "POST",
        body: JSON.stringify({ workspaceId })
      }, { admin: true });
      setSessionId(newSessionId());
      setMessages([{ id: crypto.randomUUID(), role: "system", text: "Reset complete." }]);
      await refreshStatus();
    } finally {
      setBusy(false);
    }
  }

  async function tinyBudgetDemo() {
    setBusy(true);
    try {
      const tinyBudget = {
        ...budgetForm,
        dailyBudgetUsd: "0.000001",
        monthlyBudgetUsd: "0.000001"
      };
      await request("/api/budget/configure-demo", {
        method: "POST",
        body: JSON.stringify({ workspaceId, ...budgetPayload(tinyBudget) })
      }, { admin: true });
      setBudgetForm(tinyBudget);
      setMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "system",
          text: "Tiny workspace budget applied."
        }
      ]);
      await refreshStatus();
    } finally {
      setBusy(false);
    }
  }

  async function applyCustomBudget() {
    setBusy(true);
    try {
      await request("/api/budget/configure-demo", {
        method: "POST",
        body: JSON.stringify({ workspaceId, ...budgetPayload(budgetForm) })
      }, { admin: true });
      setMessages((items) => [
        ...items,
        { id: crypto.randomUUID(), role: "system", text: "Custom budget applied." }
      ]);
      await refreshStatus();
    } catch (error) {
      setMessages((items) => [
        ...items,
        {
          id: crypto.randomUUID(),
          role: "system",
          text: error instanceof Error ? error.message : "Budget update failed."
        }
      ]);
    } finally {
      setBusy(false);
    }
  }

  function updateBudgetField(field: keyof BudgetForm, value: string) {
    setBudgetForm((current) => ({ ...current, [field]: value }));
  }

  React.useEffect(() => {
    refreshStatus().catch(() => {
      setMessages((items) => [
        ...items,
        { id: crypto.randomUUID(), role: "system", text: "Status unavailable." }
      ]);
    });
  }, []);

  return (
    <main className="shell">
      <section className="workspace-bar">
        <div className="brand-lockup">
          <img className="brand-logo" src={studioStreamXLogoUrl} alt="StudioStreamX" />
          <div>
            <h1>AI Budget Guardrails</h1>
            <p>{normalizedApiBaseUrl}</p>
          </div>
        </div>
        <div className={`state-pill ${status?.killSwitch.enabled ? "danger" : "ok"}`}>
          {status?.killSwitch.enabled ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
          <span>{status?.killSwitch.enabled ? "Kill switch on" : "Ready"}</span>
        </div>
      </section>

      <section className="layout">
        <aside className="side">
          <PanelTitle icon={<Settings2 size={18} />} title="Runtime" />
          <label>
            API
            <input value={apiBaseUrl} onChange={(event) => setApiBaseUrl(event.target.value)} />
          </label>
          <label>
            Workspace
            <input value={workspaceId} onChange={(event) => setWorkspaceId(event.target.value)} />
          </label>
          <label>
            Session
            <div className="input-row">
              <input value={sessionId} onChange={(event) => setSessionId(event.target.value)} />
              <button
                type="button"
                className="icon-button"
                onClick={() => setSessionId(newSessionId())}
                title="New session"
              >
                <RefreshCcw size={17} />
              </button>
            </div>
          </label>
          <label>
            Admin key
            <input
              type="password"
              value={adminApiKey}
              onChange={(event) => setAdminApiKey(event.target.value)}
              placeholder="Required for budget controls"
            />
          </label>

          <div className="metrics">
            <Metric label="Session" value={currency(budget?.sessionEstimatedCostUsd)} />
            <Metric label="Request" value={currency(budget?.requestEstimatedCostUsd)} />
            <Metric label="Daily" value={currency(status?.dailyEstimatedCostUsd)} />
            <Metric label="Monthly" value={currency(status?.monthlyEstimatedCostUsd)} />
          </div>

          <section className="budget-editor">
            <PanelTitle icon={<CircleDollarSign size={18} />} title="Budget" />
            <div className="budget-grid">
              <label>
                Daily USD
                <input
                  type="number"
                  min="0"
                  step="0.000001"
                  value={budgetForm.dailyBudgetUsd}
                  onChange={(event) => updateBudgetField("dailyBudgetUsd", event.target.value)}
                />
              </label>
              <label>
                Monthly USD
                <input
                  type="number"
                  min="0"
                  step="0.000001"
                  value={budgetForm.monthlyBudgetUsd}
                  onChange={(event) => updateBudgetField("monthlyBudgetUsd", event.target.value)}
                />
              </label>
              <label>
                Session USD
                <input
                  type="number"
                  min="0"
                  step="0.000001"
                  value={budgetForm.sessionBudgetUsd}
                  onChange={(event) => updateBudgetField("sessionBudgetUsd", event.target.value)}
                />
              </label>
              <label>
                Request USD
                <input
                  type="number"
                  min="0"
                  step="0.000001"
                  value={budgetForm.requestBudgetUsd}
                  onChange={(event) => updateBudgetField("requestBudgetUsd", event.target.value)}
                />
              </label>
              <label>
                Max turns
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={budgetForm.maxRequestsPerSession}
                  onChange={(event) =>
                    updateBudgetField("maxRequestsPerSession", event.target.value)
                  }
                />
              </label>
              <label>
                Max tokens
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={budgetForm.maxOutputTokens}
                  onChange={(event) => updateBudgetField("maxOutputTokens", event.target.value)}
                />
              </label>
            </div>
            <button
              type="button"
              className="apply-budget"
              onClick={applyCustomBudget}
              disabled={busy}
            >
              <Save size={16} />
              Apply Budget
            </button>
          </section>

          <div className="actions">
            <button type="button" onClick={refreshStatus} disabled={busy}>
              <RefreshCcw size={16} />
              Refresh
            </button>
            <button type="button" onClick={tinyBudgetDemo} disabled={busy}>
              <CircleDollarSign size={16} />
              Tiny Budget
            </button>
            <button type="button" onClick={() => setKillSwitch(true)} disabled={busy}>
              <Power size={16} />
              Enable
            </button>
            <button type="button" onClick={() => setKillSwitch(false)} disabled={busy}>
              <Shield size={16} />
              Disable
            </button>
            <button type="button" onClick={resetDemo} disabled={busy}>
              <RotateCcw size={16} />
              Reset
            </button>
          </div>
        </aside>

        <section className="chat">
          <div className="messages">
            {messages.map((message) => (
              <article key={message.id} className={`message ${message.role}`}>
                <div className="avatar">
                  {message.role === "user" ? <User size={16} /> : <Bot size={16} />}
                </div>
                <p>{message.text}</p>
              </article>
            ))}
          </div>
          <form
            className="composer"
            onSubmit={(event) => {
              event.preventDefault();
              sendMessage();
            }}
          >
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask a budget-safe question"
              disabled={busy}
            />
            <button type="submit" disabled={busy || !input.trim()} title="Send">
              <Send size={18} />
            </button>
          </form>
        </section>
      </section>
    </main>
  );
}

function PanelTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="panel-title">
      {icon}
      <h2>{title}</h2>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function budgetPayload(form: BudgetForm) {
  return {
    dailyBudgetUsd: Number(form.dailyBudgetUsd),
    monthlyBudgetUsd: Number(form.monthlyBudgetUsd),
    sessionBudgetUsd: Number(form.sessionBudgetUsd),
    requestBudgetUsd: Number(form.requestBudgetUsd),
    maxRequestsPerSession: Number(form.maxRequestsPerSession),
    maxOutputTokens: Number(form.maxOutputTokens)
  };
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
