# PlanO — Multi-stage Docker build
# Produces a single nginx container serving both frontends + proxying raster API

# ── Stage 1: Build PlanO UI (React + Vite) ───────────────────────────────────
FROM node:24-alpine AS plano-ui-build
WORKDIR /build
COPY 00_frontend_skeleton/plano-ui/package*.json ./
RUN npm ci --ignore-scripts
COPY 00_frontend_skeleton/plano-ui/ ./
RUN npm run build

# ── Stage 2: Build React Planner Engine (Webpack) ────────────────────────────
FROM node:24-alpine AS engine-build
WORKDIR /build
COPY 02_react_planner/react-planner/package*.json ./
COPY 02_react_planner/react-planner/yarn.lock* ./
RUN npm ci --ignore-scripts
COPY 02_react_planner/react-planner/ ./
RUN npm run build-demo

# ── Stage 3: Runtime (nginx) ─────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default site
RUN rm -f /etc/nginx/conf.d/default.conf

# Custom nginx config
COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf

# PlanO UI → served at /
COPY --from=plano-ui-build /build/dist/ /usr/share/nginx/html/

# React Planner engine → served at /engine/
# Webpack outputs to demo/ directly (app.js, index.html, assets)
COPY --from=engine-build /build/demo/ /usr/share/nginx/html/engine/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost/ || exit 1
