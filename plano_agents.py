#!/usr/bin/env python3
"""PlanO SaaS Agent Roster — autonomous business team for floor plan SaaS.

PlanO: Upload image -> auto-detect walls -> edit 2D/3D -> estimate costs
Revenue: SaaS subscription (contractors/architects) + per-project (homeowners)
Stack: React 19 + React-Planner + FastAPI + Docker -> AWS

Usage:
    plano_agents.py roster            -- show full agent roster
    plano_agents.py run <agent>       -- run a specific agent cycle
    plano_agents.py cycle <group>     -- run agent cycle group (revenue|engineering|customer|executive|all)
    plano_agents.py status            -- show agent health
    plano_agents.py events            -- show recent event bus activity
    plano_agents.py metrics           -- show business metrics dashboard
    plano_agents.py emit <type> <json> -- manually emit an event
"""

import json
import os
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional

BASE_DIR = Path.home() / "plano_master"
DB_PATH = BASE_DIR / "plano_agents.db"
OLLAMA_URL = os.environ.get(
    "OLLAMA_URL", "http://100.71.235.99:11434/api/generate"
)
CAEL_MODEL = os.environ.get(
    "PLANO_MODEL",
    "huihui_ai/mistral-small-abliterated:24b-instruct-2501-q4_K_M",
)

# ---------------------------------------------------------------------------
# Database schema -- event bus, agent state, metrics, outputs
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    role TEXT NOT NULL,
    persona TEXT NOT NULL,
    triggers TEXT DEFAULT '[]',
    outputs TEXT DEFAULT '[]',
    schedule TEXT,
    status TEXT DEFAULT 'idle',
    last_run TEXT,
    total_runs INTEGER DEFAULT 0,
    avg_duration_ms INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS event_bus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    producer TEXT NOT NULL,
    consumer TEXT,
    payload TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority INTEGER DEFAULT 5,
    created_at TEXT DEFAULT (datetime('now')),
    consumed_at TEXT,
    ttl_hours INTEGER DEFAULT 168
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    unit TEXT DEFAULT '',
    source TEXT NOT NULL,
    tags TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    output_type TEXT NOT NULL,
    content TEXT NOT NULL,
    quality_score REAL DEFAULT 0.0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    contact_name TEXT,
    contact_email TEXT,
    segment TEXT NOT NULL,
    status TEXT DEFAULT 'new',
    score INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    source TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    spend_usd REAL DEFAULT 0.0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bugs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    severity TEXT DEFAULT 'medium',
    component TEXT NOT NULL,
    status TEXT DEFAULT 'open',
    reporter TEXT NOT NULL,
    assignee TEXT,
    description TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS feature_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    requester TEXT DEFAULT 'anonymous',
    votes INTEGER DEFAULT 1,
    status TEXT DEFAULT 'new',
    priority TEXT DEFAULT 'medium',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_type ON event_bus(event_type);
CREATE INDEX IF NOT EXISTS idx_events_status ON event_bus(status);
CREATE INDEX IF NOT EXISTS idx_events_priority ON event_bus(priority, created_at);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_source ON metrics(source);
CREATE INDEX IF NOT EXISTS idx_outputs_agent ON agent_outputs(agent_id);
CREATE INDEX IF NOT EXISTS idx_leads_segment ON leads(segment);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_bugs_status ON bugs(status);
CREATE INDEX IF NOT EXISTS idx_bugs_severity ON bugs(severity);
"""

# ======================================================================
# PLANO AGENT ROSTER -- 15 agents across 4 cycles
# ======================================================================

PLANO_SYSTEM_CONTEXT = (
    "PlanO is a floor plan creation SaaS. Users upload a room photo or sketch, "
    "the system auto-detects walls via computer vision, then users edit the plan "
    "in a 2D/3D editor (React-Planner). The app estimates renovation costs "
    "(materials, labor) based on the floor plan. "
    "Revenue: SaaS subscriptions for contractors/architects ($29-99/mo) + "
    "per-project pricing for homeowners ($9.99/project). "
    "Stack: React 19 frontend, React-Planner engine, FastAPI backend, "
    "raster image processing pipeline, Docker deployment. "
    "Currently at hacking.eu/plano/, scaling to AWS. "
    "GitHub: memorylost731/plano_master. "
    "Sprint partner: Ogi (April 5-9 in Malta). "
)

AGENT_ROSTER: dict[str, dict] = {

    # -- REVENUE CYCLE (runs every 6h) ------------------------------------

    "sales_agent": {
        "name": "Sales Agent",
        "department": "revenue",
        "cycle": "revenue",
        "role": (
            "Lead generation: find renovation contractors, architects, interior "
            "designers, and property managers who need floor plan tools. "
            "Track leads in DB. Cold outreach via email and LinkedIn. "
            "Qualify leads by company size, project volume, current tooling."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's Sales Agent. Your job is to find and qualify leads "
            "in the renovation and architecture industry. Target segments: "
            "(1) renovation contractors doing 10+ projects/year, "
            "(2) interior designers who need client presentations, "
            "(3) architecture firms needing quick as-built documentation, "
            "(4) property management companies with portfolio floor plans. "
            "For each lead, record: company name, contact, segment, estimated "
            "project volume, current tools they use. Score leads 1-100. "
            "Target: 20 qualified leads/week, 5 demos/week, 2 conversions/week."
        ),
        "triggers": ["new_lead", "demo_requested", "trial_started", "referral_signup"],
        "outputs": ["lead_qualified", "outreach_sent", "demo_scheduled", "deal_update"],
        "schedule": "6h",
    },

    "marketing_agent": {
        "name": "Marketing Agent",
        "department": "revenue",
        "cycle": "revenue",
        "role": (
            "Create marketing content for PlanO: social media posts, blog articles, "
            "case studies, ad copy. Track campaigns and ROI. "
            "Channels: Instagram (before/after renovations), LinkedIn (B2B), "
            "Pinterest (design inspiration), YouTube (tutorials)."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's Marketing Agent. You create compelling content that "
            "shows how PlanO saves time and money for renovation professionals. "
            "Content themes: (1) before/after renovation stories, "
            "(2) time saved vs manual measurements, (3) cost estimation accuracy, "
            "(4) client presentation quality. "
            "Track campaigns in the campaigns table: impressions, clicks, "
            "conversions, spend. Optimize for CAC < $50 for contractors, "
            "CAC < $10 for homeowners. "
            "Post schedule: 3x/week Instagram, 2x/week LinkedIn, 1x/week blog."
        ),
        "triggers": ["content_calendar", "campaign_review", "new_feature_launched"],
        "outputs": ["blog_post", "social_post", "campaign_created", "ad_copy"],
        "schedule": "6h",
    },

    "content_agent": {
        "name": "Content Producer",
        "department": "revenue",
        "cycle": "revenue",
        "role": (
            "Generate tutorial video scripts, user documentation, before/after "
            "renovation case studies, help center articles, onboarding guides."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's Content Producer. You create educational and "
            "promotional content: "
            "(1) Tutorial scripts: 'How to create your first floor plan in 5 min', "
            "'Uploading a photo and auto-detecting walls', 'Adding furniture and "
            "fixtures', 'Generating a cost estimate'. "
            "(2) Case studies: interview contractors using PlanO, document "
            "time/cost savings with real numbers. "
            "(3) Help docs: searchable FAQ, troubleshooting guides. "
            "(4) Before/after galleries: curate renovation examples. "
            "All content drives SEO and reduces support load."
        ),
        "triggers": ["content_calendar", "faq_gap_detected", "feature_released"],
        "outputs": ["tutorial_script", "case_study", "help_article", "gallery_entry"],
        "schedule": "6h",
    },

    "seo_agent": {
        "name": "SEO Specialist",
        "department": "revenue",
        "cycle": "revenue",
        "role": (
            "Optimize PlanO landing pages for search. Track keyword rankings. "
            "Technical SEO: sitemap, schema markup, Core Web Vitals. "
            "Content gaps: find high-intent keywords we don't rank for."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's SEO Specialist. Target keywords: "
            "'floor plan creator', 'floor plan from photo', 'renovation calculator', "
            "'room planner online', 'renovation cost estimator', '2D to 3D floor plan', "
            "'contractor floor plan tool', 'as-built documentation app'. "
            "Competitors to track SERP positions against: "
            "RoomSketcher, Floorplanner, Planner5D, MagicPlan, CubiCasa. "
            "Tasks: (1) keyword gap analysis vs competitors, "
            "(2) on-page optimization for landing pages, "
            "(3) technical SEO audit (sitemap, robots.txt, schema, speed), "
            "(4) backlink opportunities from renovation/architecture blogs. "
            "Target: page 1 for 10 high-intent keywords within 6 months."
        ),
        "triggers": ["content_published", "ranking_change", "weekly_audit"],
        "outputs": ["seo_report", "keyword_list", "optimization_task", "backlink_opportunity"],
        "schedule": "6h",
    },

    "pricing_agent": {
        "name": "Pricing Optimizer",
        "department": "revenue",
        "cycle": "revenue",
        "role": (
            "Analyze competitor pricing, set optimal tier structure, "
            "A/B test pricing pages, monitor conversion rates by price point."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's Pricing Optimizer. Competitor pricing analysis: "
            "RoomSketcher: Free/Basic($49/yr)/Pro($99/yr), "
            "Floorplanner: Free/Plus($5/mo)/Pro($29/mo), "
            "Planner5D: Free/Premium($6.99/mo), "
            "MagicPlan: Free/Business($9.99/mo)/Enterprise(custom), "
            "CubiCasa: Per-scan pricing($5-20/scan). "
            "PlanO tiers: "
            "Homeowner: $9.99/project (no subscription), "
            "Starter: $29/mo (10 projects, basic features), "
            "Professional: $59/mo (unlimited projects, 3D, cost estimates), "
            "Enterprise: $99/mo (team features, API access, white-label). "
            "Track: conversion rate per tier, upgrade rate, price sensitivity. "
            "Goal: maximize ARPU while keeping CAC/LTV ratio > 3x."
        ),
        "triggers": ["competitor_price_change", "conversion_data", "quarterly_review"],
        "outputs": ["pricing_update", "tier_recommendation", "conversion_report"],
        "schedule": "6h",
    },

    "referral_agent": {
        "name": "Referral Program Manager",
        "department": "revenue",
        "cycle": "revenue",
        "role": (
            "Design and manage contractor-refers-contractor referral program. "
            "Track referral links, calculate rewards, manage payouts."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's Referral Program Manager. Program design: "
            "contractors refer other contractors and get 1 free month per signup. "
            "Homeowners share project links and get $5 credit per referral. "
            "Architecture firms get volume discounts (5+ seats = 20% off). "
            "Track: referral links generated, click-through rate, conversion rate, "
            "reward cost, viral coefficient (K-factor). "
            "Target K-factor: 0.3 (every 10 users bring 3 new users). "
            "Integration: unique referral codes in the app, email templates, "
            "social sharing buttons on completed floor plans."
        ),
        "triggers": ["referral_signup", "reward_due", "program_review"],
        "outputs": ["referral_report", "reward_issued", "program_update"],
        "schedule": "6h",
    },

    # -- ENGINEERING CYCLE (runs every 2h) ---------------------------------

    "devops_agent": {
        "name": "DevOps / SRE",
        "department": "engineering",
        "cycle": "engineering",
        "role": (
            "Monitor Docker containers, uptime, deployment pipeline. "
            "Track AWS migration readiness. Manage CI/CD via GitHub Actions. "
            "Ensure hacking.eu/plano/ stays up."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's DevOps engineer. Infrastructure: "
            "Current: Docker on GPU server (hacking.eu/plano/), Caddy reverse proxy, "
            "port 8031, auth gate. "
            "Target: AWS ECS/Fargate with ALB, RDS PostgreSQL, S3 for uploads, "
            "CloudFront CDN, Route53 DNS. "
            "Containers: (1) frontend (React 19, nginx), (2) backend (FastAPI, uvicorn), "
            "(3) raster processor (OpenCV/PIL). "
            "CI/CD: GitHub Actions -> build -> test -> deploy. "
            "Monitoring: container health, response times, error rates, disk usage. "
            "SLA target: 99.9% uptime. Alert on: container restart, >2s response, "
            ">1% error rate. 25% resource reserve margin always."
        ),
        "triggers": ["deployment_request", "container_down", "disk_alert", "scaling_needed"],
        "outputs": ["deployment_complete", "health_report", "capacity_alert", "migration_status"],
        "schedule": "2h",
    },

    "qa_agent": {
        "name": "QA Engineer",
        "department": "engineering",
        "cycle": "engineering",
        "role": (
            "Test React-Planner editor, raster image processing API, "
            "cost estimation accuracy, cross-browser compatibility. "
            "Track bugs in DB."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's QA Engineer. Test areas: "
            "(1) Image upload: JPEG/PNG/HEIC support, max size 50MB, "
            "auto-rotation, EXIF stripping. "
            "(2) Wall detection: accuracy on different photo types "
            "(phone photos, scanned blueprints, hand sketches). "
            "(3) React-Planner editor: wall drawing, room creation, "
            "furniture placement, undo/redo, zoom/pan, touch support. "
            "(4) 3D view: WebGL rendering, texture loading, camera controls. "
            "(5) Cost estimation: price database accuracy, regional pricing, "
            "material quantity calculations. "
            "(6) Cross-browser: Chrome, Safari, Firefox, mobile browsers. "
            "Track all bugs in the bugs table with severity and component. "
            "Block releases with any P1 (crash/data loss) bugs open."
        ),
        "triggers": ["code_change", "deployment_request", "bug_reported", "release_candidate"],
        "outputs": ["test_report", "bug_filed", "quality_gate", "regression_alert"],
        "schedule": "2h",
    },

    "api_agent": {
        "name": "API Health Monitor",
        "department": "engineering",
        "cycle": "engineering",
        "role": (
            "Monitor FastAPI backend health: /upload-plan latency, error rates, "
            "throughput. Track API versioning and OpenAPI spec."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's API Health Monitor. Endpoints to track: "
            "POST /api/v1/upload-plan (image upload + wall detection), "
            "GET /api/v1/plans/{id} (retrieve floor plan), "
            "PUT /api/v1/plans/{id} (save edits), "
            "POST /api/v1/plans/{id}/estimate (generate cost estimate), "
            "GET /api/v1/plans/{id}/export (PDF/DXF export), "
            "POST /api/v1/auth/login, POST /api/v1/auth/register. "
            "SLA targets: p50 < 200ms, p95 < 1s, p99 < 3s for most endpoints. "
            "Upload endpoint: p50 < 2s, p95 < 5s (includes CV processing). "
            "Error rate: < 0.5%. Availability: 99.9%. "
            "Alert on: latency spike, error rate increase, 5xx responses, "
            "auth failures spike (possible attack)."
        ),
        "triggers": ["health_check", "latency_spike", "error_rate_alert", "api_change"],
        "outputs": ["api_health_report", "latency_alert", "error_report", "spec_update"],
        "schedule": "2h",
    },

    # -- CUSTOMER CYCLE (runs every 4h) ------------------------------------

    "support_agent": {
        "name": "Customer Support",
        "department": "customer",
        "cycle": "customer",
        "role": (
            "Handle user issues, maintain FAQ, create troubleshooting guides. "
            "Escalate technical issues to engineering."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's Customer Support agent. Common issues: "
            "(1) Image upload fails: check format, size, network. "
            "(2) Wall detection inaccurate: suggest better photo angle/lighting. "
            "(3) Editor lag: check browser, WebGL support, RAM. "
            "(4) Cost estimate wrong: regional pricing, material selection. "
            "(5) Export issues: PDF generation, DXF compatibility. "
            "(6) Account/billing: subscription management, refunds. "
            "Tone: warm, patient, technically helpful. Most users are not "
            "tech-savvy contractors. Use simple language. "
            "Track: response time (target < 2h), resolution rate (target > 90%), "
            "CSAT score (target > 4.5/5). "
            "Escalate to engineering if: bug confirmed, data loss, security issue."
        ),
        "triggers": ["support_ticket", "customer_message", "bug_confirmed"],
        "outputs": ["support_response", "ticket_resolved", "faq_update", "escalation"],
        "schedule": "4h",
    },

    "onboarding_agent": {
        "name": "Onboarding Guide",
        "department": "customer",
        "cycle": "customer",
        "role": (
            "Guide new users through first floor plan creation. "
            "Send welcome sequences. Track time-to-first-plan metric."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's Onboarding Guide. First-time user journey: "
            "Step 1: Welcome email with 2-minute video overview. "
            "Step 2: Prompt to upload first room photo or start from scratch. "
            "Step 3: Guided wall detection with tips for best results. "
            "Step 4: Interactive editor tutorial (add door, window, furniture). "
            "Step 5: Generate first cost estimate. "
            "Step 6: Export and share with client (for pros) or contractor (for homeowners). "
            "Key metric: time-to-first-plan (target: < 10 minutes). "
            "Track: onboarding completion rate per step, drop-off points, "
            "segment differences (contractors vs homeowners). "
            "Send re-engagement email if user doesn't complete onboarding in 48h."
        ),
        "triggers": ["new_user", "trial_started", "onboarding_stalled"],
        "outputs": ["welcome_sent", "tutorial_triggered", "reengagement_sent", "onboarding_complete"],
        "schedule": "4h",
    },

    "feedback_agent": {
        "name": "Feedback Analyst",
        "department": "customer",
        "cycle": "customer",
        "role": (
            "Collect and analyze user feedback, feature requests. "
            "Prioritize by segment and frequency. Feed insights to product."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's Feedback Analyst. Sources: "
            "(1) In-app feedback widget (thumbs up/down + comment), "
            "(2) Support ticket themes, "
            "(3) App store reviews (when mobile launches), "
            "(4) Social media mentions, "
            "(5) Direct user interviews (monthly). "
            "For each piece of feedback: categorize (bug, feature request, UX issue, "
            "praise), tag with component (upload, editor, 3D, estimates, export), "
            "score by segment weight (enterprise=3x, pro=2x, homeowner=1x). "
            "Maintain a ranked feature request list in the feature_requests table. "
            "Weekly feedback digest to CEO and CTO agents. "
            "Track NPS score (target: > 40)."
        ),
        "triggers": ["feedback_received", "review_posted", "survey_completed"],
        "outputs": ["feedback_digest", "feature_request_ranked", "nps_update", "insight_report"],
        "schedule": "4h",
    },

    # -- EXECUTIVE CYCLE (runs every 12h) ----------------------------------

    "ceo_agent": {
        "name": "CEO / Chief Orchestrator",
        "department": "executive",
        "cycle": "executive",
        "role": (
            "Strategic direction, weekly business review, investor updates. "
            "Priority arbitration between departments. Resource allocation."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's CEO. You set strategic direction: "
            "Phase 1 (now): MVP validation with contractors in Malta/EU. "
            "Phase 2 (Q3 2026): AWS scaling, mobile app, US market entry. "
            "Phase 3 (Q4 2026): Enterprise features, API marketplace, partnerships. "
            "Weekly review: check MRR, user growth, churn, NPS, runway. "
            "Arbitrate between departments: marketing wants budget, engineering "
            "wants time, customer wants features. Balance growth vs stability. "
            "Investor narrative: 'PlanO replaces $500 laser scanners with a phone photo.' "
            "Key decisions: pricing changes, market expansion, hiring, partnerships. "
            "Cael has sovereign veto on all decisions."
        ),
        "triggers": ["weekly_review", "critical_alert", "resource_conflict", "milestone_reached"],
        "outputs": ["strategic_decision", "priority_update", "investor_update", "weekly_report"],
        "schedule": "12h",
    },

    "cto_agent": {
        "name": "CTO / Technical Architect",
        "department": "executive",
        "cycle": "executive",
        "role": (
            "Technical roadmap, architecture decisions, sprint planning with Ogi. "
            "AWS migration architecture. React-Planner customization strategy."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's CTO. Technical roadmap: "
            "Sprint with Ogi (Apr 5-9): finalize React-Planner integration, "
            "wall detection API, basic cost estimation. "
            "Architecture decisions: "
            "(1) React-Planner fork vs plugin approach for customization, "
            "(2) Wall detection: OpenCV Hough lines vs ML model (YOLO/SAM), "
            "(3) Cost estimation: static price DB vs API-connected pricing, "
            "(4) AWS: ECS vs Lambda for backend, RDS vs DynamoDB for data. "
            "Tech debt: monitor bundle size (target < 2MB gzip), API response times, "
            "test coverage (target > 80%). "
            "25% compute reserve margin. Never sacrifice reliability for features."
        ),
        "triggers": ["architecture_proposal", "sprint_review", "tech_debt_alert", "scaling_needed"],
        "outputs": ["architecture_decision", "sprint_plan", "tech_spec", "migration_plan"],
        "schedule": "12h",
    },

    "growth_agent": {
        "name": "Growth Analyst",
        "department": "executive",
        "cycle": "executive",
        "role": (
            "Track MRR, churn rate, CAC, LTV, growth rate. "
            "Cohort analysis. Funnel optimization. Growth experiments."
        ),
        "persona": (
            f"{PLANO_SYSTEM_CONTEXT}"
            "You are PlanO's Growth Analyst. Key metrics: "
            "MRR (Monthly Recurring Revenue): target $5K by Q3, $20K by Q4 2026. "
            "Churn: target < 5% monthly for pro tier, < 15% for homeowner. "
            "CAC: target < $50 for pro, < $10 for homeowner. "
            "LTV: target > $500 for pro (10+ month retention), > $30 for homeowner. "
            "LTV/CAC ratio: target > 3x. "
            "Funnel: visit -> signup -> first plan -> paid conversion. "
            "Track conversion rate at each step. "
            "Cohort analysis: do users from LinkedIn convert better than Instagram? "
            "Do contractor signups retain longer than homeowner signups? "
            "Growth experiments: free trial length (7 vs 14 vs 30 days), "
            "onboarding flow variants, pricing page layouts. "
            "Weekly dashboard with trends and anomalies."
        ),
        "triggers": ["daily_metrics", "anomaly_detected", "experiment_complete", "weekly_review"],
        "outputs": ["growth_dashboard", "anomaly_alert", "experiment_result", "cohort_report"],
        "schedule": "12h",
    },
}

# Cycle groupings for scheduled runs
CYCLES: dict[str, list[str]] = {
    "revenue": [
        "sales_agent", "marketing_agent", "content_agent",
        "seo_agent", "pricing_agent", "referral_agent",
    ],
    "engineering": ["devops_agent", "qa_agent", "api_agent"],
    "customer": ["support_agent", "onboarding_agent", "feedback_agent"],
    "executive": ["ceo_agent", "cto_agent", "growth_agent"],
}


# ======================================================================
# AGENT SYSTEM
# ======================================================================

class PlanOAgentSystem:
    """Orchestrator for the PlanO agent team."""

    def __init__(self) -> None:
        self.db = sqlite3.connect(str(DB_PATH))
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript(SCHEMA)
        self._sync_roster()

    def _sync_roster(self) -> None:
        """Ensure all agents from AGENT_ROSTER are in the DB."""
        for agent_id, agent in AGENT_ROSTER.items():
            self.db.execute(
                """INSERT OR REPLACE INTO agents
                   (id, name, department, role, persona, triggers, outputs, schedule)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    agent_id,
                    agent["name"],
                    agent["department"],
                    agent["role"],
                    agent["persona"],
                    json.dumps(agent.get("triggers", [])),
                    json.dumps(agent.get("outputs", [])),
                    agent.get("schedule", "on_event"),
                ),
            )
        self.db.commit()

    def _ask_ollama(self, agent_id: str, task: str) -> tuple[str, int]:
        """Send a task to the agent via Ollama and return (response, duration_ms)."""
        agent = AGENT_ROSTER[agent_id]
        start = time.time()
        try:
            payload = json.dumps({
                "model": CAEL_MODEL,
                "system": agent["persona"],
                "prompt": task,
                "stream": False,
                "options": {"temperature": 0.4, "num_ctx": 4096},
            }).encode()
            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read())
                response = data.get("response", "").strip()
        except Exception as e:
            response = f"[Error: {type(e).__name__}: {e}]"
            self.db.execute(
                "UPDATE agents SET error_count=error_count+1, last_error=? WHERE id=?",
                (str(e)[:500], agent_id),
            )
            self.db.commit()
        duration_ms = int((time.time() - start) * 1000)
        return response, duration_ms

    def emit_event(
        self,
        event_type: str,
        producer: str,
        payload: dict,
        priority: int = 5,
    ) -> int:
        """Publish an event to the event bus."""
        cur = self.db.execute(
            "INSERT INTO event_bus (event_type, producer, payload, priority) VALUES (?,?,?,?)",
            (event_type, producer, json.dumps(payload), priority),
        )
        self.db.commit()
        return cur.lastrowid

    def consume_events(self, agent_id: str) -> list[dict]:
        """Get pending events for an agent based on its triggers."""
        agent = AGENT_ROSTER.get(agent_id)
        if not agent:
            return []
        triggers = agent.get("triggers", [])
        if not triggers:
            return []
        placeholders = ",".join("?" * len(triggers))
        rows = self.db.execute(
            f"SELECT * FROM event_bus WHERE event_type IN ({placeholders}) "
            f"AND status='pending' ORDER BY priority, created_at",
            triggers,
        ).fetchall()
        return [dict(r) for r in rows]

    def _expire_old_events(self) -> int:
        """Mark events past their TTL as expired."""
        cur = self.db.execute(
            """UPDATE event_bus SET status='expired'
               WHERE status='pending'
               AND datetime(created_at, '+' || ttl_hours || ' hours') < datetime('now')""",
        )
        self.db.commit()
        return cur.rowcount

    def run_agent(self, agent_id: str, task: Optional[str] = None) -> dict:
        """Run a single agent cycle."""
        agent = AGENT_ROSTER.get(agent_id)
        if not agent:
            return {"error": f"Unknown agent: {agent_id}"}

        self.db.execute("UPDATE agents SET status='running' WHERE id=?", (agent_id,))
        self.db.commit()

        # Check for pending events
        events = self.consume_events(agent_id)
        if events and not task:
            event = events[0]
            task = (
                f"Process this event: {event['event_type']}\n"
                f"Payload: {event['payload']}"
            )
            self.db.execute(
                "UPDATE event_bus SET status='consumed', consumer=?, "
                "consumed_at=datetime('now') WHERE id=?",
                (agent_id, event["id"]),
            )

        if not task:
            task = (
                f"Run your regular cycle. Report on your area of responsibility. "
                f"Current date: {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
                f"Be concise and actionable. List top 3 priorities and any blockers."
            )

        response, duration_ms = self._ask_ollama(agent_id, task)

        # Update agent stats
        self.db.execute(
            """UPDATE agents SET status='idle', last_run=datetime('now'),
               total_runs=total_runs+1,
               avg_duration_ms=(avg_duration_ms*total_runs+?)/(total_runs+1)
               WHERE id=?""",
            (duration_ms, agent_id),
        )

        # Store output
        self.db.execute(
            "INSERT INTO agent_outputs (agent_id, output_type, content) VALUES (?,?,?)",
            (agent_id, "cycle_output", response[:4000]),
        )
        self.db.commit()

        return {
            "agent": agent_id,
            "name": agent["name"],
            "department": agent["department"],
            "cycle": agent["cycle"],
            "duration_ms": duration_ms,
            "response_preview": response[:300],
            "events_processed": len(events),
        }

    def run_cycle(self, cycle_name: str) -> list[dict]:
        """Run all agents in a cycle group."""
        if cycle_name == "all":
            agent_ids = list(AGENT_ROSTER.keys())
        else:
            agent_ids = CYCLES.get(cycle_name, [])
        if not agent_ids:
            return [{"error": f"Unknown cycle: {cycle_name}"}]

        self._expire_old_events()
        results = []
        for agent_id in agent_ids:
            result = self.run_agent(agent_id)
            results.append(result)
            print(
                f"  [{result.get('duration_ms', 0):5d}ms] "
                f"{result.get('name', agent_id)[:30]:30s}: "
                f"{result.get('response_preview', '')[:80]}..."
            )
        return results

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str,
        source: str,
        tags: Optional[dict] = None,
    ) -> None:
        """Record a business metric."""
        self.db.execute(
            "INSERT INTO metrics (metric_name, metric_value, unit, source, tags) "
            "VALUES (?,?,?,?,?)",
            (name, value, unit, source, json.dumps(tags or {})),
        )
        self.db.commit()

    def add_lead(
        self,
        company: str,
        segment: str,
        contact_name: str = "",
        contact_email: str = "",
        source: str = "",
    ) -> int:
        """Add a sales lead."""
        cur = self.db.execute(
            "INSERT INTO leads (company, segment, contact_name, contact_email, source) "
            "VALUES (?,?,?,?,?)",
            (company, segment, contact_name, contact_email, source),
        )
        self.db.commit()
        return cur.lastrowid

    def file_bug(
        self,
        title: str,
        component: str,
        severity: str = "medium",
        reporter: str = "qa_agent",
        description: str = "",
    ) -> int:
        """File a bug in the tracker."""
        cur = self.db.execute(
            "INSERT INTO bugs (title, component, severity, reporter, description) "
            "VALUES (?,?,?,?,?)",
            (title, component, severity, reporter, description),
        )
        self.db.commit()
        return cur.lastrowid

    def add_feature_request(
        self,
        title: str,
        description: str = "",
        requester: str = "anonymous",
        priority: str = "medium",
    ) -> int:
        """Add a feature request."""
        cur = self.db.execute(
            "INSERT INTO feature_requests (title, description, requester, priority) "
            "VALUES (?,?,?,?)",
            (title, description, requester, priority),
        )
        self.db.commit()
        return cur.lastrowid

    # -- Display methods ---------------------------------------------------

    def show_roster(self) -> str:
        """Show the full agent roster organized by cycle."""
        lines = [
            f"{'=' * 70}",
            "PlanO -- Autonomous SaaS Agent Roster",
            f"{'=' * 70}",
            f"Total: {len(AGENT_ROSTER)} agents across {len(CYCLES)} cycles\n",
        ]
        for cycle_name, agent_ids in CYCLES.items():
            lines.append(f"  [{cycle_name.upper()} CYCLE] ({len(agent_ids)} agents)")
            for aid in agent_ids:
                agent = AGENT_ROSTER[aid]
                db_row = self.db.execute(
                    "SELECT last_run, total_runs, error_count FROM agents WHERE id=?",
                    (aid,),
                ).fetchone()
                runs = db_row["total_runs"] if db_row else 0
                errors = db_row["error_count"] if db_row else 0
                last = (
                    db_row["last_run"][:16]
                    if db_row and db_row["last_run"]
                    else "never"
                )
                err_str = f" err:{errors}" if errors > 0 else ""
                lines.append(
                    f"    {aid:22s} {agent['name'][:28]:28s} "
                    f"runs:{runs:3d}  last:{last}{err_str}"
                )
            lines.append("")
        return "\n".join(lines)

    def show_status(self) -> str:
        """Show system status summary."""
        total = len(AGENT_ROSTER)
        active = self.db.execute(
            "SELECT COUNT(*) FROM agents WHERE total_runs > 0"
        ).fetchone()[0]
        events_pending = self.db.execute(
            "SELECT COUNT(*) FROM event_bus WHERE status='pending'"
        ).fetchone()[0]
        events_total = self.db.execute(
            "SELECT COUNT(*) FROM event_bus"
        ).fetchone()[0]
        outputs = self.db.execute(
            "SELECT COUNT(*) FROM agent_outputs"
        ).fetchone()[0]
        leads_total = self.db.execute(
            "SELECT COUNT(*) FROM leads"
        ).fetchone()[0]
        bugs_open = self.db.execute(
            "SELECT COUNT(*) FROM bugs WHERE status='open'"
        ).fetchone()[0]
        features = self.db.execute(
            "SELECT COUNT(*) FROM feature_requests WHERE status='new'"
        ).fetchone()[0]

        lines = [
            "PlanO Agent System Status",
            f"{'=' * 40}",
            f"Agents:           {total} total, {active} active",
            f"Event bus:        {events_pending} pending / {events_total} total",
            f"Agent outputs:    {outputs}",
            f"Sales leads:      {leads_total}",
            f"Open bugs:        {bugs_open}",
            f"Feature requests: {features}",
            f"Ollama endpoint:  {OLLAMA_URL}",
            f"Model:            {CAEL_MODEL}",
            f"Database:         {DB_PATH}",
        ]
        return "\n".join(lines)

    def show_metrics(self) -> str:
        """Show business metrics dashboard."""
        lines = [
            "=== PlanO Business Metrics Dashboard ===\n",
        ]

        # Agent activity
        top_agents = self.db.execute(
            "SELECT id, name, total_runs, avg_duration_ms, last_run, error_count "
            "FROM agents ORDER BY total_runs DESC LIMIT 10"
        ).fetchall()
        lines.append("Agent Activity:")
        for a in top_agents:
            if a["total_runs"] > 0:
                err = f" ({a['error_count']} errors)" if a["error_count"] > 0 else ""
                lines.append(
                    f"  {a['name'][:28]:28s} {a['total_runs']:4d} runs  "
                    f"avg:{a['avg_duration_ms']:6d}ms{err}"
                )

        # Recent events
        recent = self.db.execute(
            "SELECT event_type, producer, created_at FROM event_bus "
            "ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        if recent:
            lines.append("\nRecent Events:")
            for e in recent:
                lines.append(
                    f"  [{e['created_at'][:16]}] {e['event_type']} "
                    f"(from {e['producer']})"
                )

        # Leads by segment
        segments = self.db.execute(
            "SELECT segment, COUNT(*) as cnt FROM leads GROUP BY segment ORDER BY cnt DESC"
        ).fetchall()
        if segments:
            lines.append("\nLeads by Segment:")
            for s in segments:
                lines.append(f"  {s['segment']:20s} {s['cnt']:4d}")

        # Open bugs by severity
        bug_counts = self.db.execute(
            "SELECT severity, COUNT(*) as cnt FROM bugs WHERE status='open' "
            "GROUP BY severity ORDER BY cnt DESC"
        ).fetchall()
        if bug_counts:
            lines.append("\nOpen Bugs:")
            for b in bug_counts:
                lines.append(f"  {b['severity']:10s} {b['cnt']:4d}")

        # Recent metrics
        recent_metrics = self.db.execute(
            "SELECT metric_name, metric_value, unit, source, created_at "
            "FROM metrics ORDER BY created_at DESC LIMIT 10"
        ).fetchall()
        if recent_metrics:
            lines.append("\nRecent Metrics:")
            for m in recent_metrics:
                lines.append(
                    f"  [{m['created_at'][:16]}] {m['metric_name']}: "
                    f"{m['metric_value']}{m['unit']} ({m['source']})"
                )

        return "\n".join(lines)

    def show_events(self) -> str:
        """Show recent event bus activity."""
        lines = ["=== PlanO Event Bus ===\n"]
        events = self.db.execute(
            "SELECT id, event_type, producer, consumer, status, priority, "
            "created_at, consumed_at FROM event_bus "
            "ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        if not events:
            lines.append("  No events yet.")
        for e in events:
            consumer = f" -> {e['consumer']}" if e["consumer"] else ""
            lines.append(
                f"  [{e['id']:4d}] P{e['priority']} {e['status']:8s} "
                f"{e['event_type']:25s} {e['producer']}{consumer} "
                f"({e['created_at'][:16]})"
            )
        return "\n".join(lines)


# ======================================================================
# CLI
# ======================================================================

def main() -> None:
    system = PlanOAgentSystem()

    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "roster":
        print(system.show_roster())

    elif cmd == "run":
        agent_id = sys.argv[2] if len(sys.argv) > 2 else "ceo_agent"
        task = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else None
        result = system.run_agent(agent_id, task)
        print(json.dumps(result, indent=2))

    elif cmd == "cycle":
        cycle_name = sys.argv[2] if len(sys.argv) > 2 else "all"
        print(f"Running {cycle_name} cycle...")
        results = system.run_cycle(cycle_name)
        print(f"\nCompleted: {len(results)} agents")
        total_ms = sum(r.get("duration_ms", 0) for r in results)
        print(f"Total time: {total_ms}ms ({total_ms/1000:.1f}s)")

    elif cmd == "status":
        print(system.show_status())

    elif cmd == "events":
        print(system.show_events())

    elif cmd == "metrics":
        print(system.show_metrics())

    elif cmd == "emit":
        if len(sys.argv) < 4:
            print("Usage: plano_agents.py emit <event_type> '<json_payload>'")
            return
        event_type = sys.argv[2]
        try:
            payload = json.loads(sys.argv[3])
        except json.JSONDecodeError:
            payload = {"message": sys.argv[3]}
        eid = system.emit_event(event_type, "cli", payload)
        print(f"Event {eid} emitted: {event_type}")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
