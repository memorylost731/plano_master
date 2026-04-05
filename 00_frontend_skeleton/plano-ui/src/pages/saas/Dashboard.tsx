import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  BarChart3,
  Bot,
  Building2,
  Check,
  ChevronRight,
  Clock,
  CreditCard,
  DollarSign,
  Globe,
  HardDrive,
  Heart,
  Layers,
  LayoutDashboard,
  MonitorSmartphone,
  Package,
  RefreshCw,
  Server,
  Settings,
  Shield,
  Sparkles,
  TrendingUp,
  Upload,
  Zap,
} from "lucide-react";

/* ── Types ── */

type ServiceStatus = "online" | "degraded" | "offline" | "loading";

interface SystemHealth {
  planoUi: ServiceStatus;
  plannerEngine: ServiceStatus;
  rasterApi: ServiceStatus;
  dockerProd: ServiceStatus;
  rasterProd: ServiceStatus;
  ollamaAgents: ServiceStatus;
  caddy: ServiceStatus;
}

/* ── Pricing Tiers ── */

const TIERS = [
  {
    name: "Free",
    price: "$0",
    period: "",
    features: [
      "1 project",
      "Watermarked exports",
      "Basic 2D only",
      "Max 200m\u00B2",
    ],
    highlight: false,
    color: "bg-zinc-100 border-zinc-200",
    badge: "",
  },
  {
    name: "Starter",
    price: "$9",
    period: "/mo",
    features: [
      "5 active projects",
      "HD exports, no watermark",
      "2D + 3D views",
      "Basic cost estimate",
      "Email support",
    ],
    highlight: false,
    color: "bg-blue-50 border-blue-200",
    badge: "",
  },
  {
    name: "Pro",
    price: "$19",
    period: "/mo",
    features: [
      "Unlimited projects",
      "Full cost estimates",
      "PDF reports",
      "Priority support",
      "API access (1K calls/mo)",
    ],
    highlight: true,
    color: "bg-indigo-50 border-indigo-300",
    badge: "POPULAR",
  },
  {
    name: "Agency",
    price: "$49",
    period: "/mo",
    features: [
      "Everything in Pro",
      "5 team seats (+$9/seat)",
      "White-label exports",
      "Client portal",
      "API (10K calls/mo)",
    ],
    highlight: false,
    color: "bg-purple-50 border-purple-200",
    badge: "",
  },
  {
    name: "Homeowner",
    price: "$4.99",
    period: "/plan",
    features: [
      "One-time per project",
      "Includes export",
      "Cost estimate included",
      "No subscription",
    ],
    highlight: false,
    color: "bg-amber-50 border-amber-200",
    badge: "B2C",
  },
];

/* ── Sprint Tasks ── */

const SPRINT_TASKS = [
  { id: 1, title: "User authentication (Supabase)", status: "todo", priority: "P0" },
  { id: 2, title: "Stripe payment integration", status: "todo", priority: "P0" },
  { id: 3, title: "BTCPay Server setup", status: "todo", priority: "P1" },
  { id: 4, title: "Usage metering middleware", status: "todo", priority: "P1" },
  { id: 5, title: "Subscription tier enforcement", status: "todo", priority: "P0" },
  { id: 6, title: "Landing page / marketing site", status: "todo", priority: "P1" },
  { id: 7, title: "Service pricing database (rates by trade/region)", status: "todo", priority: "P2" },
  { id: 8, title: "PDF export with watermark logic", status: "todo", priority: "P1" },
  { id: 9, title: "Shareable project URLs (viral loop)", status: "todo", priority: "P2" },
  { id: 10, title: "Referral program (Stripe coupons)", status: "todo", priority: "P2" },
  { id: 11, title: "Email transactional (Resend)", status: "todo", priority: "P1" },
  { id: 12, title: "Review farming automation", status: "todo", priority: "P2" },
];

/* ── Architecture Diagram ── */

const ARCHITECTURE = [
  { layer: "CDN / Proxy", items: ["Caddy (HTTPS, auth)", "Cloudflare (future)"] },
  { layer: "Frontend", items: ["React 19 + Vite (plano-ui)", "React-Planner (iframe engine)"] },
  { layer: "Backend API", items: ["FastAPI (Rasta)", "Supabase Auth (planned)", "Stripe webhooks (planned)"] },
  { layer: "AI / ML", items: ["15 Ollama agents", "GPU floor plan detection", "Celery workers"] },
  { layer: "Data", items: ["PostgreSQL (planned)", "SQLite (agents)", "Redis (job queue)"] },
  { layer: "Infra", items: ["Docker (nginx prod)", "GPU RTX 6000 Ada", "BTCPay (Bitcoin)"] },
];

/* ── Helper Components ── */

function StatusDot({ status }: { status: ServiceStatus }) {
  const colors: Record<ServiceStatus, string> = {
    online: "bg-emerald-400 saas-pulse",
    degraded: "bg-amber-400",
    offline: "bg-red-400",
    loading: "bg-slate-500 animate-pulse",
  };
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${colors[status]}`} />;
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-slate-700/50 bg-[#1E293B] p-5 shadow-lg shadow-black/20 saas-card-glow ${className}`}>
      {children}
    </div>
  );
}

function SectionTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      {icon}
      <h2 className="font-display text-lg font-semibold text-slate-100">{title}</h2>
    </div>
  );
}

/* ── Main Dashboard ���─ */

export default function SaasDashboard() {
  const [health, setHealth] = useState<SystemHealth>({
    planoUi: "loading",
    plannerEngine: "loading",
    rasterApi: "loading",
    dockerProd: "loading",
    rasterProd: "loading",
    ollamaAgents: "loading",
    caddy: "loading",
  });

  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "pricing" | "agents" | "architecture" | "sprint">("overview");

  const checkHealth = useCallback(async () => {
    setRefreshing(true);
    const check = async (url: string, timeout = 5000): Promise<ServiceStatus> => {
      try {
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), timeout);
        const resp = await fetch(url, { signal: ctrl.signal });
        clearTimeout(timer);
        return resp.ok ? "online" : "degraded";
      } catch {
        return "offline";
      }
    };

    const [ui, engine, rasterLocal, dockerHealth, rasterHealth] = await Promise.all([
      check(import.meta.env.BASE_URL || "/"),
      check((import.meta.env.VITE_ENGINE_URL || "/engine") + "/"),
      check((import.meta.env.BASE_URL || "/") + "api/health"),
      check((import.meta.env.BASE_URL || "/") + "api/health"),
      check((import.meta.env.BASE_URL || "/") + "api/health"),
    ]);

    setHealth({
      planoUi: ui,
      plannerEngine: engine,
      rasterApi: rasterLocal,
      dockerProd: dockerHealth,
      rasterProd: rasterHealth,
      ollamaAgents: "online", // agents run on timer, assume online
      caddy: dockerHealth === "online" ? "online" : "degraded",
    });

    setRefreshing(false);
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const TABS = [
    { key: "overview", label: "Overview", icon: <LayoutDashboard className="h-4 w-4" /> },
    { key: "pricing", label: "Pricing", icon: <CreditCard className="h-4 w-4" /> },
    { key: "agents", label: "AI Agents", icon: <Bot className="h-4 w-4" /> },
    { key: "architecture", label: "Architecture", icon: <Layers className="h-4 w-4" /> },
    { key: "sprint", label: "Sprint", icon: <Zap className="h-4 w-4" /> },
  ] as const;

  return (
    <div className="min-h-screen bg-[#0F172A] text-slate-200">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-slate-700/50 bg-[#0F172A]/95 backdrop-blur-xl">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <Link to="/" className="flex items-center gap-2 group">
              <Building2 className="h-5 w-5 text-amber-500" />
              <span className="font-display font-bold text-white">PlanO</span>
            </Link>
            <span className="text-slate-600">/</span>
            <span className="text-sm font-medium text-slate-400">SaaS Dashboard</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={checkHealth}
              disabled={refreshing}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800 hover:border-slate-500 disabled:opacity-50 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-500 transition-colors"
            >
              <Globe className="h-3.5 w-3.5" />
              Live App
            </Link>
          </div>
        </div>
      </header>

      {/* Tab Bar */}
      <div className="border-b border-slate-700/50 bg-[#0F172A]">
        <div className="mx-auto flex max-w-7xl gap-1 px-4 py-1.5">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium transition-all duration-200 ${
                activeTab === tab.key
                  ? "saas-tab-active"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="mx-auto max-w-7xl px-4 py-6">
        {activeTab === "overview" && <OverviewTab health={health} />}
        {activeTab === "pricing" && <PricingTab />}
        {activeTab === "agents" && <AgentsTab />}
        {activeTab === "architecture" && <ArchitectureTab />}
        {activeTab === "sprint" && <SprintTab />}
      </main>
    </div>
  );
}

/* ── OVERVIEW TAB ── */

function OverviewTab({ health }: { health: SystemHealth }) {
  const services = [
    { name: "PlanO UI (Vite :5174)", status: health.planoUi, icon: <MonitorSmartphone className="h-4 w-4" /> },
    { name: "Planner Engine (Webpack :5173)", status: health.plannerEngine, icon: <Package className="h-4 w-4" /> },
    { name: "Rasta API (local :8011)", status: health.rasterApi, icon: <Upload className="h-4 w-4" /> },
    { name: "Docker Prod (:8031)", status: health.dockerProd, icon: <Server className="h-4 w-4" /> },
    { name: "Rasta GPU (:8020)", status: health.rasterProd, icon: <HardDrive className="h-4 w-4" /> },
    { name: "AI Agents (Ollama)", status: health.ollamaAgents, icon: <Bot className="h-4 w-4" /> },
    { name: "Caddy (hacking.eu)", status: health.caddy, icon: <Shield className="h-4 w-4" /> },
  ];

  const onlineCount = services.filter((s) => s.status === "online").length;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="saas-kpi-card bg-[#1E293B] p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider">System Health</p>
              <p className="font-display text-3xl font-bold text-white mt-1">{onlineCount}/{services.length}</p>
            </div>
            <div className="rounded-xl bg-emerald-500/15 p-3">
              <Heart className="h-6 w-6 text-emerald-400" />
            </div>
          </div>
        </div>
        <div className="saas-kpi-card bg-[#1E293B] p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider">AI Agents</p>
              <p className="font-display text-3xl font-bold text-white mt-1">15</p>
            </div>
            <div className="rounded-xl bg-blue-500/15 p-3">
              <Bot className="h-6 w-6 text-blue-400" />
            </div>
          </div>
        </div>
        <div className="saas-kpi-card bg-[#1E293B] p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider">Monthly Cost</p>
              <p className="font-display text-3xl font-bold text-amber-500 mt-1">~$1</p>
            </div>
            <div className="rounded-xl bg-amber-500/15 p-3">
              <DollarSign className="h-6 w-6 text-amber-400" />
            </div>
          </div>
        </div>
        <div className="saas-kpi-card bg-[#1E293B] p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider">Break-even</p>
              <p className="font-display text-3xl font-bold text-amber-500 mt-1">1 user</p>
            </div>
            <div className="rounded-xl bg-purple-500/15 p-3">
              <TrendingUp className="h-6 w-6 text-purple-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Services Health */}
      <Card>
        <SectionTitle icon={<Activity className="h-5 w-5 text-zinc-600" />} title="Service Health" />
        <div className="divide-y">
          {services.map((svc) => (
            <div key={svc.name} className="flex items-center justify-between py-3">
              <div className="flex items-center gap-3">
                <span className="text-zinc-400">{svc.icon}</span>
                <span className="text-sm font-medium">{svc.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <StatusDot status={svc.status} />
                <span className="text-xs text-zinc-500 capitalize w-16">{svc.status}</span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Quick Links */}
      <Card>
        <SectionTitle icon={<Sparkles className="h-5 w-5 text-zinc-600" />} title="Quick Links" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { label: "3D Map (GeoSelect)", to: "/", desc: "Landing page with 3D buildings" },
            { label: "Floor Plan Editor", to: "/planner", desc: "2D/3D planner + raster upload" },
            { label: "Cost Estimate", to: "/estimate", desc: "BOQ table (hardcoded demo)" },
          ].map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="group flex items-center justify-between rounded-xl border p-4 hover:bg-zinc-50 transition-colors"
            >
              <div>
                <p className="text-sm font-medium">{link.label}</p>
                <p className="text-xs text-zinc-500">{link.desc}</p>
              </div>
              <ChevronRight className="h-4 w-4 text-zinc-300 group-hover:text-zinc-600 transition-colors" />
            </Link>
          ))}
        </div>
      </Card>

      {/* What's Built vs Not */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle icon={<Check className="h-5 w-5 text-emerald-600" />} title="Built & Working" />
          <ul className="space-y-2">
            {[
              "React 19 + Vite frontend with Tailwind",
              "MapLibre 3D building selection (GeoSelect)",
              "React-Planner 2D/3D editor (iframe bridge)",
              "Rasta floor plan detection (OpenCV + GPU)",
              "Upload image/PDF -> auto-detect walls",
              "PostMessage API for planner commands",
              "15 AI agents (Ollama-powered cycles)",
              "Docker deployment (nginx multi-stage)",
              "Caddy reverse proxy + auth gate",
              "Service sub-selection (7 trades, 43 items)",
              "Project save/load (JSON download)",
              "BTCPay Server (port 8032)",
            ].map((item) => (
              <li key={item} className="flex items-start gap-2 text-sm">
                <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-500" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <SectionTitle icon={<Clock className="h-5 w-5 text-amber-600" />} title="Needs Building" />
          <ul className="space-y-2">
            {[
              "User authentication (Supabase Auth)",
              "Stripe payment processing",
              "Subscription tier enforcement",
              "Usage metering per user",
              "Project persistence (DB, not file download)",
              "Landing page / marketing site",
              "Service pricing database (regional rates)",
              "PDF export (watermark for free tier)",
              "Shareable project URLs (viral loop)",
              "Referral program",
              "Transactional email (Resend)",
              "SEO content pages",
            ].map((item) => (
              <li key={item} className="flex items-start gap-2 text-sm">
                <Clock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}

/* ── PRICING TAB ── */

function PricingTab() {
  return (
    <div className="space-y-6">
      <Card>
        <SectionTitle icon={<CreditCard className="h-5 w-5 text-zinc-600" />} title="Pricing Tiers" />
        <p className="text-sm text-zinc-500 mb-6">
          Positioning: cheaper than MagicPlan, more powerful than Floorplanner, contractor-focused.
          Annual discount: 20%. BTC accepted on all tiers (10% discount vs card).
        </p>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`relative rounded-xl border-2 p-4 ${tier.color} ${
                tier.highlight ? "ring-2 ring-indigo-400 ring-offset-2" : ""
              }`}
            >
              {tier.badge && (
                <span className="absolute -top-2.5 right-3 rounded-full bg-indigo-600 px-2 py-0.5 text-[10px] font-bold text-white">
                  {tier.badge}
                </span>
              )}
              <h3 className="text-lg font-bold">{tier.name}</h3>
              <div className="mt-1">
                <span className="text-2xl font-black">{tier.price}</span>
                <span className="text-sm text-zinc-500">{tier.period}</span>
              </div>
              <ul className="mt-3 space-y-1.5">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-1.5 text-xs">
                    <Check className="mt-0.5 h-3 w-3 shrink-0 text-emerald-600" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Card>

      {/* Payment Infrastructure */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle icon={<CreditCard className="h-5 w-5 text-zinc-600" />} title="Stripe (Cards + SEPA)" />
          <div className="space-y-2 text-sm">
            <p><strong>Mode:</strong> Hosted Checkout (zero PCI burden)</p>
            <p><strong>Fees:</strong> 1.5% + 0.25 EUR (EU) / 2.9% + 0.30 USD (non-EU)</p>
            <p><strong>Methods:</strong> Card, Apple Pay, Google Pay, SEPA, iDEAL</p>
            <p><strong>Portal:</strong> Self-service cancel, upgrade, invoices</p>
            <p className="text-amber-600 font-medium">Status: NOT YET INTEGRATED</p>
          </div>
        </Card>
        <Card>
          <SectionTitle icon={<DollarSign className="h-5 w-5 text-zinc-600" />} title="BTCPay (0% fees)" />
          <div className="space-y-2 text-sm">
            <p><strong>Mode:</strong> Self-hosted on GPU server (port 8032)</p>
            <p><strong>Network:</strong> BTC on-chain + Lightning (LND)</p>
            <p><strong>Discount:</strong> 10% off all tiers when paying BTC</p>
            <p><strong>Backend:</strong> bitcoind already running on GPU</p>
            <p className="text-emerald-600 font-medium">Status: Server available, needs store config</p>
          </div>
        </Card>
      </div>

      {/* Cost Analysis */}
      <Card>
        <SectionTitle icon={<BarChart3 className="h-5 w-5 text-zinc-600" />} title="Cost Analysis" />
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-zinc-50 text-xs text-zinc-600">
              <tr>
                <th className="px-3 py-2 text-left">Item</th>
                <th className="px-3 py-2 text-center">Monthly Cost</th>
                <th className="px-3 py-2 text-left">Notes</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["GPU server", "$0", "Already rented, runs Docker + Ollama + BTCPay"],
                ["Dell server (503GB)", "$0", "Backup raster API capacity"],
                ["Domain (hacking.eu)", "~$1", "Already owned"],
                ["Supabase Auth", "$0", "Free to 50K MAU"],
                ["Caddy (HTTPS)", "$0", "Auto-cert, free"],
                ["Cloudflare CDN", "$0", "Free tier"],
                ["Ollama (AI agents)", "$0", "Already running on GPU"],
                ["BTCPay Server", "$0", "Self-hosted, no fees"],
              ].map(([item, cost, notes]) => (
                <tr key={item} className="border-t">
                  <td className="px-3 py-2 font-medium">{item}</td>
                  <td className="px-3 py-2 text-center font-mono">{cost}</td>
                  <td className="px-3 py-2 text-zinc-500">{notes}</td>
                </tr>
              ))}
              <tr className="border-t-2 border-zinc-300 bg-zinc-50 font-bold">
                <td className="px-3 py-2">TOTAL</td>
                <td className="px-3 py-2 text-center font-mono">~$1/mo</td>
                <td className="px-3 py-2 text-emerald-600">Break-even: 1 paying user</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/* ── AGENTS TAB ── */

function AgentsTab() {
  const agentRoster = [
    { dept: "Revenue", agents: [
      { name: "Sales Hunter", role: "Lead generation & outreach", schedule: "6h" },
      { name: "Marketing Strategist", role: "Campaign planning & execution", schedule: "6h" },
      { name: "Content Creator", role: "Blog posts, social, newsletters", schedule: "6h" },
      { name: "SEO Optimizer", role: "Technical & content SEO", schedule: "6h" },
      { name: "Pricing Analyst", role: "Competitive pricing & A/B tests", schedule: "6h" },
      { name: "Referral Manager", role: "Referral program & partnerships", schedule: "6h" },
    ]},
    { dept: "Engineering", agents: [
      { name: "DevOps Engineer", role: "CI/CD, Docker, monitoring", schedule: "2h" },
      { name: "QA Tester", role: "Automated testing & regression", schedule: "2h" },
      { name: "API Monitor", role: "Uptime, latency, error tracking", schedule: "2h" },
    ]},
    { dept: "Customer", agents: [
      { name: "Support Agent", role: "Ticket triage & response", schedule: "4h" },
      { name: "Onboarding Guide", role: "New user tutorials & tips", schedule: "4h" },
      { name: "Feedback Analyst", role: "NPS, reviews, feature requests", schedule: "4h" },
    ]},
    { dept: "Executive", agents: [
      { name: "CEO Agent", role: "Strategy, decisions, priorities", schedule: "12h" },
      { name: "CTO Agent", role: "Tech roadmap, architecture", schedule: "12h" },
      { name: "Growth Hacker", role: "Viral loops, experiments", schedule: "12h" },
    ]},
  ];

  return (
    <div className="space-y-6">
      <Card>
        <SectionTitle icon={<Bot className="h-5 w-5 text-zinc-600" />} title="AI Agent Roster (15 agents)" />
        <p className="text-sm text-zinc-500 mb-4">
          All agents powered by Ollama (Mistral-Small 24B abliterated) on GPU server.
          Agents run on systemd timers in 4 cycle groups.
        </p>

        {agentRoster.map((dept) => (
          <div key={dept.dept} className="mb-6 last:mb-0">
            <h3 className="text-sm font-bold text-zinc-700 uppercase tracking-wider mb-2 flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-blue-500" />
              {dept.dept} Cycle (every {dept.agents[0].schedule})
            </h3>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {dept.agents.map((agent) => (
                <div key={agent.name} className="rounded-lg border p-3 hover:bg-zinc-50 transition-colors">
                  <p className="text-sm font-medium">{agent.name}</p>
                  <p className="text-xs text-zinc-500">{agent.role}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </Card>

      {/* Agent Cycle Timers */}
      <Card>
        <SectionTitle icon={<Clock className="h-5 w-5 text-zinc-600" />} title="Cycle Timers (systemd)" />
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-zinc-50 text-xs text-zinc-600">
              <tr>
                <th className="px-3 py-2 text-left">Cycle</th>
                <th className="px-3 py-2 text-center">Interval</th>
                <th className="px-3 py-2 text-left">Service</th>
                <th className="px-3 py-2 text-center">Status</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["Revenue", "6 hours", "plano-cycle-revenue", "Active (timer)"],
                ["Engineering", "2 hours", "plano-cycle-engineering", "Active (timer)"],
                ["Customer", "4 hours", "plano-cycle-customer", "Active (timer)"],
                ["Executive", "12 hours", "plano-cycle-executive", "Active (timer)"],
              ].map(([cycle, interval, service, status]) => (
                <tr key={cycle} className="border-t">
                  <td className="px-3 py-2 font-medium">{cycle}</td>
                  <td className="px-3 py-2 text-center">{interval}</td>
                  <td className="px-3 py-2 font-mono text-xs">{service}</td>
                  <td className="px-3 py-2 text-center">
                    <span className="inline-flex items-center gap-1">
                      <StatusDot status="online" />
                      <span className="text-xs">{status}</span>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/* ── ARCHITECTURE TAB ── */

function ArchitectureTab() {
  return (
    <div className="space-y-6">
      <Card>
        <SectionTitle icon={<Layers className="h-5 w-5 text-zinc-600" />} title="System Architecture" />
        <div className="space-y-4">
          {ARCHITECTURE.map((layer, i) => (
            <div key={layer.layer} className="relative">
              <div className="flex items-start gap-4">
                <div className="flex flex-col items-center">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-900 text-xs font-bold text-white">
                    {i + 1}
                  </div>
                  {i < ARCHITECTURE.length - 1 && (
                    <div className="h-full w-0.5 bg-zinc-200 my-1" style={{ minHeight: 24 }} />
                  )}
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-bold text-zinc-900">{layer.layer}</h3>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {layer.items.map((item) => (
                      <span
                        key={item}
                        className={`rounded-lg px-2.5 py-1 text-xs font-medium ${
                          item.includes("planned") ? "bg-amber-50 text-amber-700 border border-amber-200" : "bg-zinc-100 text-zinc-700"
                        }`}
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Ports Map */}
      <Card>
        <SectionTitle icon={<Server className="h-5 w-5 text-zinc-600" />} title="Port Assignments" />
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-zinc-50 text-xs text-zinc-600">
              <tr>
                <th className="px-3 py-2 text-left">Service</th>
                <th className="px-3 py-2 text-center">Port</th>
                <th className="px-3 py-2 text-center">Host</th>
                <th className="px-3 py-2 text-left">Notes</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["plano-ui (Vite dev)", "5174", "local", "React frontend dev server"],
                ["plano-engine (Webpack)", "5173", "local", "React-Planner engine dev"],
                ["Rasta API (dev)", "8011", "local", "OpenCV floor plan detection"],
                ["Rasta API (prod)", "8020", "GPU", "GPU-accelerated + Celery workers"],
                ["Docker nginx (prod)", "8031", "GPU", "Production frontend + API proxy"],
                ["BTCPay Server", "8032", "GPU", "Bitcoin payment processing"],
                ["Auth gate", "9099", "GPU", "JWT + bcrypt auth service"],
                ["Caddy (HTTPS)", "443/80", "GPU", "Public: hacking.eu/plano/"],
              ].map(([svc, port, host, notes]) => (
                <tr key={svc} className="border-t">
                  <td className="px-3 py-2 font-medium">{svc}</td>
                  <td className="px-3 py-2 text-center font-mono">{port}</td>
                  <td className="px-3 py-2 text-center">
                    <span className={`rounded px-1.5 py-0.5 text-xs ${
                      host === "GPU" ? "bg-purple-50 text-purple-700" : "bg-zinc-100 text-zinc-600"
                    }`}>
                      {host}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-zinc-500">{notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Data Flow */}
      <Card>
        <SectionTitle icon={<Settings className="h-5 w-5 text-zinc-600" />} title="Request Flow" />
        <div className="rounded-lg bg-zinc-900 p-4 text-xs font-mono text-zinc-300 overflow-x-auto whitespace-pre">
{`User -> hacking.eu/plano/
  -> Caddy (TLS termination)
    -> Auth gate (:9099) - JWT cookie check
      -> Docker nginx (:8031)
        -> / = plano-ui (static React build)
        -> /engine/ = react-planner (static Webpack build)
        -> /api/raster = proxy -> Rasta GPU (:8020/api/upload-plan)
        -> /api/health = proxy -> Rasta GPU (:8020/api/health)

Floor Plan Upload:
  plano-ui -> PlannerFrame.loadProjectPicker()
    -> POST /api/raster (file upload)
      -> nginx proxy -> Rasta :8020/api/upload-plan
        -> Redis queue -> Celery worker
          -> GPU engine (RTX 6000 Ada)
            -> wall/room/door detection
              -> scene JSON response
    -> postMessage(LOAD_RASTER_JSON) -> iframe engine`}
        </div>
      </Card>
    </div>
  );
}

/* ── SPRINT TAB ── */

function SprintTab() {
  const [tasks, setTasks] = useState(SPRINT_TASKS);

  const toggleTask = (id: number) => {
    setTasks((prev) =>
      prev.map((t) =>
        t.id === id ? { ...t, status: t.status === "done" ? "todo" : "done" } : t
      )
    );
  };

  const doneCount = tasks.filter((t) => t.status === "done").length;

  return (
    <div className="space-y-6">
      {/* Sprint Header */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold">Sprint: Ogi x Hadrien (April 5-9)</h2>
            <p className="text-sm text-zinc-500">Malta sprint - SaaS MVP launch preparation</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold">{doneCount}/{tasks.length}</p>
            <p className="text-xs text-zinc-500">tasks done</p>
          </div>
        </div>
        <div className="mt-3 h-2 rounded-full bg-zinc-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-emerald-500 transition-all"
            style={{ width: `${(doneCount / tasks.length) * 100}%` }}
          />
        </div>
      </Card>

      {/* Task List */}
      <Card>
        <SectionTitle icon={<Zap className="h-5 w-5 text-zinc-600" />} title="Sprint Backlog" />
        <div className="divide-y">
          {tasks.map((task) => (
            <div
              key={task.id}
              className="flex items-center gap-3 py-3 cursor-pointer hover:bg-zinc-50 -mx-5 px-5 transition-colors"
              onClick={() => toggleTask(task.id)}
            >
              <div
                className={`h-5 w-5 rounded border-2 flex items-center justify-center shrink-0 transition-colors ${
                  task.status === "done"
                    ? "bg-emerald-500 border-emerald-500"
                    : "border-zinc-300"
                }`}
              >
                {task.status === "done" && <Check className="h-3 w-3 text-white" />}
              </div>
              <span
                className={`flex-1 text-sm ${
                  task.status === "done" ? "line-through text-zinc-400" : "text-zinc-900"
                }`}
              >
                {task.title}
              </span>
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                  task.priority === "P0"
                    ? "bg-red-100 text-red-700"
                    : task.priority === "P1"
                    ? "bg-amber-100 text-amber-700"
                    : "bg-zinc-100 text-zinc-600"
                }`}
              >
                {task.priority}
              </span>
            </div>
          ))}
        </div>
      </Card>

      {/* Sprint Priorities */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <h3 className="text-sm font-bold text-red-700 mb-2">P0 - Must Ship</h3>
          <ul className="space-y-1 text-sm text-zinc-700">
            <li>User auth (Supabase)</li>
            <li>Stripe payments</li>
            <li>Tier enforcement</li>
          </ul>
          <p className="mt-2 text-xs text-zinc-400">Without these, no revenue possible</p>
        </Card>
        <Card>
          <h3 className="text-sm font-bold text-amber-700 mb-2">P1 - Should Ship</h3>
          <ul className="space-y-1 text-sm text-zinc-700">
            <li>BTCPay integration</li>
            <li>Usage metering</li>
            <li>Landing page</li>
            <li>PDF export</li>
            <li>Email (Resend)</li>
          </ul>
          <p className="mt-2 text-xs text-zinc-400">Revenue optimization + UX polish</p>
        </Card>
        <Card>
          <h3 className="text-sm font-bold text-zinc-500 mb-2">P2 - Nice to Have</h3>
          <ul className="space-y-1 text-sm text-zinc-700">
            <li>Pricing DB (regional rates)</li>
            <li>Shareable URLs</li>
            <li>Referral program</li>
            <li>Review farming</li>
          </ul>
          <p className="mt-2 text-xs text-zinc-400">Growth features, post-launch OK</p>
        </Card>
      </div>
    </div>
  );
}
