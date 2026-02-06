# Novartis Planner — AWS Architecture (Deck & Demo)

This document is intended for creating an **architecture and demo deck** for running Novartis Planner (Congress Twin) on AWS.

---

## 1. High-Level AWS Architecture

```
                                    Internet
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  AWS Cloud                                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │  VPC (e.g. 10.0.0.0/16)                                               │   │
│  │  • Public subnets (for ALB, NAT)                                      │   │
│  │  • Private subnets (for ECS tasks, RDS)                               │   │
│  │                                                                       │   │
│  │  ┌─────────────────┐     ┌─────────────────────────────────────────┐  │   │
│  │  │  ALB            │     │  Private subnet                         │  │   │
│  │  │  (HTTPS :443)   │────▶│  • ECS Fargate (Backend API :8010)      │  │   │
│  │  │  or             │     │  • ECS Fargate or EC2 (Frontend :3000)  │  │   │
│  │  │  CloudFront     │     │    or use Amplify for Next.js           │  │   │
│  │  └────────┬────────┘     └─────────────────────────────────────────┘  │   │
│  │           │                            │                               │   │
│  │           │                            ▼                               │   │
│  │           │                 ┌─────────────────────┐                    │   │
│  │           │                 │  RDS (Postgres)      │                    │   │
│  │           │                 │  • planner_tasks    │                    │   │
│  │           │                 │  • plan_sync_state  │                    │   │
│  │           │                 │  • external_events  │                    │   │
│  │           │                 │  • agent_proposed_*  │                    │   │
│  │           │                 └─────────────────────┘                    │   │
│  │           │                                                             │   │
│  │  ┌────────▼────────┐       Optional: Neo4j (EC2 or managed)            │   │
│  │  │  Amplify Hosting │       Optional: Secrets Manager (DB, Graph)      │   │
│  │  │  (Next.js app)   │                                                    │   │
│  │  └─────────────────┘                                                    │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Recommended AWS Services

| Component | AWS service | Purpose |
|-----------|-------------|--------|
| **Frontend** | **Amplify Hosting** or **S3 + CloudFront** | Next.js static/SSR. Amplify: connect repo, build Next.js, deploy. Alternative: build locally and deploy to S3 + CloudFront. |
| **Backend API** | **ECS Fargate** or **EC2** | Run FastAPI (uvicorn) on port 8010. One task or small Auto Scaling group. |
| **Load balancing** | **ALB** | Route traffic to ECS tasks (backend). Optional: separate ALB or path-based routing for API vs frontend if not using Amplify. |
| **Database** | **RDS for Postgres** | Store planner_tasks, plan_sync_state, external_events, agent_proposed_actions. Run migrations (001–005) on RDS. |
| **Secrets** | **Secrets Manager** | Store RDS credentials, optional MS Graph client id/secret/tenant, Neo4j URL if used. |
| **Networking** | **VPC, public/private subnets, security groups** | Backend and RDS in private subnets; ALB in public. Restrict RDS to backend security group only. |
| **Optional** | **Neo4j on EC2** or managed | If graph features are used later. |

---

## 3. Deployment Options (for Deck)

### Option A: Amplify + ECS + RDS (recommended for demo)

1. **RDS**: Create Postgres instance in private subnet. Run migrations, note endpoint and secret.
2. **ECS**: Build Docker image for Congress Twin backend (FastAPI). Push to ECR. Create ECS Fargate service with task definition (env: `PG_HOST`, `PG_DATABASE`, etc. from Secrets Manager or task env). Port 8010.
3. **ALB**: Create Application Load Balancer; target group → ECS service (8010). HTTPS listener (ACM certificate).
4. **Amplify**: Connect repo (e.g. `congress-twin/frontend` or monorepo with build settings for Next.js). Set env var `NEXT_PUBLIC_CONGRESS_TWIN_API_URL` = ALB URL (e.g. `https://api-demo.example.com`). Deploy.
5. **Security groups**: ALB allows 443 from internet; ECS allows 8010 from ALB; RDS allows 5432 from ECS only.

### Option B: Single EC2 (quick demo)

1. **EC2**: One Amazon Linux or Ubuntu instance (e.g. t3.small). Install Docker (or Python/Node directly).
2. **RDS**: Postgres in same VPC; security group allows 5432 from EC2.
3. **Run backend**: In container or venv, set `PG_HOST` to RDS endpoint, run migrations, then `uvicorn congress_twin.main:app --host 0.0.0.0 --port 8010`.
4. **Run frontend**: Build Next.js with `NEXT_PUBLIC_CONGRESS_TWIN_API_URL=http://<EC2-private-IP>:8010` or use ALB in front of EC2 and set that URL. Serve with `npm run start` or PM2.
5. **Access**: Put ALB in front of EC2 (ports 3000 and 8010) or use EC2 public IP and open 3000/8010 for a quick demo (less secure).

---

## 4. Environment Variables (AWS)

- **Backend (ECS/EC2)**  
  - `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_DATABASE` (from RDS).  
  - `CORS_ORIGINS`: include Amplify/frontend origin (e.g. `https://main.xxxx.amplifyapp.com`).  
  - Optional: `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, `GRAPH_TENANT_ID` (from Secrets Manager).  
  - Optional: `NEO_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` if using Neo4j.

- **Frontend (Amplify)**  
  - `NEXT_PUBLIC_CONGRESS_TWIN_API_URL`: backend API base URL (ALB or API gateway), e.g. `https://api-demo.example.com`.

---

## 5. Diagram Points for Deck

1. **User** → Browser → **Amplify** (Next.js) or **CloudFront** (frontend).
2. **Frontend** → `NEXT_PUBLIC_CONGRESS_TWIN_API_URL` → **ALB** → **ECS (Backend)**.
3. **Backend** → **RDS Postgres** (planner_tasks, plan_sync_state, external_events, agent_proposed_actions).
4. **Optional**: Backend → **MS Graph** (Planner sync); secrets in **Secrets Manager**.
5. **Security**: VPC, private subnets for backend and RDS; only ALB and Amplify/CloudFront in public-facing layers.

---

## 6. Demo Checklist (AWS)

- [ ] RDS Postgres created; migrations 001–005 applied.
- [ ] Backend running on ECS or EC2; env points to RDS; CORS includes frontend origin.
- [ ] Frontend built with correct `NEXT_PUBLIC_CONGRESS_TWIN_API_URL` and deployed (Amplify or S3+CloudFront).
- [ ] Sync/Seed executed once so planner has data.
- [ ] Open frontend URL → Base view (Attention, Critical Path, Milestone Lane, Dependency Lens) and Advanced view (Monte Carlo, Mitigation Feed, Pending Approvals).
- [ ] Optional: Ingest external event via REST; show Alerts and approve/reject in UI.

This gives you a clear **overall architecture** and **AWS-specific architecture** for the deck and for running the demo on AWS.
