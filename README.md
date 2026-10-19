# SupportIQ — Customer Support Operations Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue.svg)](https://www.docker.com/)
[![Baserow](https://img.shields.io/badge/Baserow-REST_API-green.svg)](https://baserow.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![Apache Superset](https://img.shields.io/badge/Apache_Superset-BI-orange.svg)](https://superset.apache.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

From support tickets to actionable operational insights. **SupportIQ** is an end-to-end support operations analytics platform that ingests operational ticket data from Baserow via REST API, processes and normalizes it through a Python/Pandas ETL pipeline, calculates real-time **SLA Risk Scores**, stores analytical models in PostgreSQL, generates **Evidence-Based Manager Insights**, and presents BI dashboards in Apache Superset.

---

## 🌟 Architecture Overview

```
┌──────────────────────────────────────────────┐
│  Baserow (Operational Ticket Entry / Storage)│  <-- REST API (Port 8000)
└──────────────────────┬───────────────────────┘
                       │ Ingestion
                       ▼
┌──────────────────────────────────────────────┐
│  Python ETL Pipeline (Pandas + SQLAlchemy)   │  <-- SLA Risk Score Engine
└──────────────────────┬───────────────────────┘
                       │ Upsert / Batch Load
                       ▼
┌──────────────────────────────────────────────┐
│  PostgreSQL Analytics Store                  │  <-- Star Schema + SQL Views (Port 5433)
└──────────────────────┬───────────────────────┘
                       │ Connection
                       ▼
┌──────────────────────────────────────────────┐
│  Apache Superset BI & Flask Operational UI   │  <-- Decision Dashboards (Port 8088 / 5050)
└──────────────────────────────────────────────┘
```

---

## 🚀 Key Features

1. **Baserow Operational Layer**: Real-time REST API integration with 1,284+ seeded operational tickets, agents, customers, and product catalogs.
2. **SLA Breach Risk Engine**: Evaluates active open tickets with continuous risk scoring:
   $$\text{SLA Risk Score} = \frac{\text{elapsed\_hours}}{\text{allowed\_SLA\_hours}}$$
   Classifies tickets into `Low Risk`, `Medium Risk`, `High Risk`, and `Breached`.
3. **Manager Insights Engine**: Automated evidence-based insight blocks identifying high-volume category surges, operational bottlenecks, and recommended capacity adjustments.
4. **PostgreSQL Star Schema & Views**: Optimized schema with `dim_agents`, `dim_customers`, `dim_products`, `fact_tickets`, `ops.tickets`, `v_executive_kpis`, `v_agent_performance`, `v_sla_risk_queue`, and `v_customer_issue_intelligence`.
5. **Apache Superset BI Integration**: Automated REST database connector script and 3 specialized operational dashboards.
6. **Unified Flask Ops Console & Intake**: Single Flask web app with shared navbar (`base.html`), Blueprint-modularized ticket intake (`web/intake`), parameterized SQL writes into `ops.tickets`, live status updates, executive KPIs, and SLA Risk Queue (`http://localhost:5050`).


---

## 🛠️ Quick Start

### 1. Clone & Setup Environment
```bash
git clone https://github.com/raunaknayak12/SupportIQ.git
cd SupportIQ
pip install -r requirements.txt
```

### 2. Launch Services
```bash
docker compose up -d
```

### 3. Seed Baserow & Run ETL Pipeline
```bash
python etl/seed_baserow.py
python etl/pipeline.py
```

### 4. Connect Superset Automatically
```bash
python superset/connect_superset.py
```

### 5. Launch Operational Console
```bash
python web/app.py
```
Open your browser at `http://localhost:5050`.

---

## 📊 Superset Dashboards Guide

Refer to [superset/DASHBOARD_BUILD_GUIDE.md](superset/DASHBOARD_BUILD_GUIDE.md) for step-by-step instructions on creating:
1. **Executive Support Overview**
2. **Agent Performance**
3. **Customer & Issue Intelligence**

---

## 🧪 Unit Tests
Run unit tests with pytest:
```bash
pytest tests/
```
