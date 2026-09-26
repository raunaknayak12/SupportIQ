# SupportIQ — Apache Superset Dashboard Creation Guide

This guide provides step-by-step instructions for creating the 3 core decision-making operational dashboards in Apache Superset using the pre-registered `SupportIQ Analytics DB` datasets.

---

## Prerequisites
- Apache Superset running at `http://localhost:8088` (Credentials: `admin` / `admin`).
- Database `SupportIQ Analytics DB` registered.
- Datasets registered: `fact_tickets`, `v_executive_kpis`, `v_agent_performance`, `v_sla_risk_queue`, `v_customer_issue_intelligence`.

---

## Dashboard 1 — Executive Support Overview

### Objective
High-level operational overview for Support VP / Managers showing volume, resolution speed, SLA compliance %, and issue category distribution.

### Step-by-Step Building Instructions:
1. Navigate to **Dashboards** -> Click **+ Dashboard** -> Title: `SupportIQ - Executive Support Overview`.
2. **Create KPI Card Charts**:
   - Go to **Charts** -> Click **+ Chart**.
   - Dataset: `v_executive_kpis` -> Chart Type: `Big Number`.
   - Metrics to create:
     - **Total Tickets**: Metric `MAX(total_tickets)` -> Save as `KPI - Total Tickets`.
     - **SLA Compliance %**: Metric `MAX(sla_compliance_pct)` -> Save as `KPI - SLA Compliance %`.
     - **Avg Resolution Time**: Metric `MAX(avg_resolution_hours)` -> Save as `KPI - Avg Resolution Time (hrs)`.
     - **Avg CSAT**: Metric `MAX(avg_csat)` -> Save as `KPI - Avg CSAT`.
3. **Create Distribution & Trend Charts**:
   - **Tickets Over Time**: Dataset `fact_tickets` -> Chart Type: `Time-series Line Chart` -> Time Column: `created_at` -> Metric: `COUNT(*)` -> Group By: `status`.
   - **Tickets by Priority**: Dataset `fact_tickets` -> Chart Type: `Pie Chart` -> Dimension: `priority` -> Metric: `COUNT(*)`.
   - **Tickets by Category**: Dataset `fact_tickets` -> Chart Type: `Bar Chart` -> X-Axis: `category` -> Metric: `COUNT(*)`.
   - **SLA Compliance Trend**: Dataset `fact_tickets` -> Chart Type: `Time-series Bar Chart` -> Group By: `is_sla_breached`.
4. **Layout**:
   - Drag KPI Big Numbers across the top row.
   - Place `Tickets Over Time` and `Tickets by Category` in the middle grid.
   - Place `Tickets by Priority` and `SLA Compliance Trend` in the lower grid.

---

## Dashboard 2 — Agent Performance

### Objective
Filterable operational view for Team Leads to track resolution velocity, SLA compliance by agent/team, CSAT, and open backlog.

### Step-by-Step Building Instructions:
1. Navigate to **Dashboards** -> Click **+ Dashboard** -> Title: `SupportIQ - Agent Performance`.
2. Add Dashboard Filters:
   - Click **Native Filters** on the left panel.
   - Add Filters for: `Team` (Column: `team`), `Region` (Column: `region`), `Date Range` (Column: `created_at`).
3. **Create Charts**:
   - **Tickets Handled by Agent**: Dataset `v_agent_performance` -> Chart Type: `Bar Chart` -> X-Axis: `agent_name` -> Metric: `MAX(total_handled)` -> Group By: `team`.
   - **Avg Resolution Time by Agent**: Dataset `v_agent_performance` -> Chart Type: `Bar Chart` -> X-Axis: `agent_name` -> Metric: `MAX(avg_resolution_hours)`.
   - **SLA Compliance Rate by Agent**: Dataset `v_agent_performance` -> Chart Type: `Bar Chart` -> X-Axis: `agent_name` -> Metric: `MAX(sla_compliance_pct)` (Add threshold line at 85%).
   - **CSAT Rating by Agent**: Dataset `v_agent_performance` -> Chart Type: `Bar Chart` -> X-Axis: `agent_name` -> Metric: `MAX(avg_csat)`.
   - **Open Backlog per Agent**: Dataset `v_agent_performance` -> Chart Type: `Bar Chart` -> X-Axis: `agent_name` -> Metric: `MAX(open_backlog)`.

---

## Dashboard 3 — Customer & Issue Intelligence

### Objective
Deep-dive intelligence for Product & Support Operations managers analyzing product failure rates, regional trends, and repeat complaints.

### Step-by-Step Building Instructions:
1. Navigate to **Dashboards** -> Click **+ Dashboard** -> Title: `SupportIQ - Customer & Issue Intelligence`.
2. **Create Charts**:
   - **Most Common Support Issues**: Dataset `v_customer_issue_intelligence` -> Chart Type: `Bar Chart` -> X-Axis: `category` -> Metric: `SUM(ticket_count)`.
   - **Product-wise Complaint Breakdown**: Dataset `v_customer_issue_intelligence` -> Chart Type: `Treemap` or `Pie Chart` -> Dimension: `product_name` -> Metric: `SUM(ticket_count)`.
   - **Customer Segment vs Ticket Volume**: Dataset `v_customer_issue_intelligence` -> Chart Type: `Stacked Bar Chart` -> X-Axis: `customer_segment` -> Metric: `SUM(ticket_count)` -> Breakdown: `category`.
   - **Region-wise Ticket Distribution**: Dataset `v_customer_issue_intelligence` -> Chart Type: `Bar Chart` -> X-Axis: `customer_region` -> Metric: `SUM(ticket_count)`.
   - **CSAT by Issue Category**: Dataset `v_customer_issue_intelligence` -> Chart Type: `Bar Chart` -> X-Axis: `category` -> Metric: `AVG(avg_csat)`.
