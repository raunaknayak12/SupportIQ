# SupportIQ — Apache Superset Dashboard Construction Guide

This step-by-step guide provides explicit instructions for constructing all **3 Operational Support Dashboards** in Apache Superset (`http://localhost:8088`) using the automatically registered datasets:
- **Database**: `SupportIQ Analytics DB`
- **Registered Datasets**: `fact_tickets`, `v_executive_kpis`, `v_agent_performance`, `v_sla_risk_queue`, `v_customer_issue_intelligence`.
- **Reference Guide**: See also [`superset/DASHBOARD_BUILD_GUIDE.md`](superset/DASHBOARD_BUILD_GUIDE.md) for supplementary chart layouts and native filters.

---

## 📊 Dashboard 1: Executive Support Overview

**Goal**: Executive-level view of ticket volumes, SLA compliance, resolution performance, and issue breakdowns.

### Step 1: Create Dashboard Container
1. Open Apache Superset (`http://localhost:8088`).
2. Navigate to **Dashboards** -> Click **+ Dashboard**.
3. Title: `SupportIQ — Executive Support Overview`.
4. Click **Save**.

### Step 2: Build KPI Cards
Create 6 Big Number KPI cards using dataset `v_executive_kpis`:
1. **Total Tickets**: Chart Type: *Big Number*, Metric: `MAX(total_tickets)`.
2. **Open Backlog**: Chart Type: *Big Number*, Metric: `MAX(open_tickets)`.
3. **Resolved Tickets**: Chart Type: *Big Number*, Metric: `MAX(resolved_tickets)`.
4. **SLA Compliance %**: Chart Type: *Big Number with Trendline*, Metric: `MAX(sla_compliance_pct)` (Format: `0.0%`).
5. **Avg Resolution Time**: Chart Type: *Big Number*, Metric: `MAX(avg_resolution_hours)` (Format: `0.0h`).
6. **Avg CSAT**: Chart Type: *Big Number*, Metric: `MAX(avg_csat)` (Format: `0.00 / 5.0`).

### Step 3: Build Core Charts
1. **Tickets Volume Over Time**:
   - Dataset: `fact_tickets`
   - Chart Type: *Time-series Line Chart*
   - X-Axis: `created_at` (Group by: `Day` or `Week`)
   - Metrics: `COUNT(ticket_id)`
   - Color / Dimension: `status`
2. **Tickets by Priority Distribution**:
   - Dataset: `fact_tickets`
   - Chart Type: *Pie / Donut Chart*
   - Dimension: `priority`
   - Metric: `COUNT(ticket_id)`
3. **Tickets by Category Breakdown**:
   - Dataset: `fact_tickets`
   - Chart Type: *Bar Chart (Horizontal)*
   - Y-Axis: `category`
   - Metric: `COUNT(ticket_id)`
   - Sort: Descending
4. **Top 10 Support Issue Types**:
   - Dataset: `fact_tickets`
   - Chart Type: *Table / Bar Chart*
   - Group by: `category`, `product_id`
   - Metrics: `COUNT(ticket_id)`, `AVG(resolution_hours)`

---

## 📈 Dashboard 2: Agent Performance

**Goal**: Monitor support agent throughput, resolution speed, SLA compliance rates, and active workload backlog.

### Step 1: Create Dashboard Container
1. Navigate to **Dashboards** -> Click **+ Dashboard**.
2. Title: `SupportIQ — Agent Performance`.
3. Add Global Filter Bar: Filters for `team`, `region`, `agent_name`, `date_range`.

### Step 2: Build Agent Metrics & Charts
1. **Tickets Handled by Agent**:
   - Dataset: `v_agent_performance`
   - Chart Type: *Bar Chart*
   - X-Axis: `agent_name`
   - Metric: `MAX(total_handled)`
   - Color: `team`
2. **Average Resolution Time by Agent**:
   - Dataset: `v_agent_performance`
   - Chart Type: *Bar Chart*
   - X-Axis: `agent_name`
   - Metric: `MAX(avg_resolution_hours)`
3. **SLA Compliance % by Agent**:
   - Dataset: `v_agent_performance`
   - Chart Type: *Bar Chart*
   - X-Axis: `agent_name`
   - Metric: `MAX(sla_compliance_pct)`
   - Threshold Line: 85%
4. **CSAT Score by Agent**:
   - Dataset: `v_agent_performance`
   - Chart Type: *Bar Chart*
   - X-Axis: `agent_name`
   - Metric: `MAX(avg_csat)`
5. **Open Backlog Queue per Agent**:
   - Dataset: `v_agent_performance`
   - Chart Type: *Stacked Bar Chart*
   - X-Axis: `agent_name`
   - Metrics: `MAX(open_backlog)`

---

## 🔍 Dashboard 3: Customer & Issue Intelligence

**Goal**: Analyze root-cause product complaints, customer segment volume trends, regional friction points, and repeat complaints.

### Step 1: Create Dashboard Container
1. Navigate to **Dashboards** -> Click **+ Dashboard**.
2. Title: `SupportIQ — Customer & Issue Intelligence`.

### Step 2: Build Intelligence Charts
1. **Most Common Support Issues**:
   - Dataset: `v_customer_issue_intelligence`
   - Chart Type: *Treemap / Bar Chart*
   - Group by: `category`
   - Metric: `SUM(ticket_count)`
2. **Product-wise Complaint Breakdown**:
   - Dataset: `v_customer_issue_intelligence`
   - Chart Type: *Stacked Bar Chart*
   - X-Axis: `product_name`
   - Dimension: `category`
   - Metric: `SUM(ticket_count)`
3. **Customer Segment vs Ticket Volume**:
   - Dataset: `v_customer_issue_intelligence`
   - Chart Type: *Pie / Donut Chart*
   - Dimension: `customer_segment`
   - Metric: `SUM(ticket_count)`
4. **Region-wise Ticket Distribution**:
   - Dataset: `v_customer_issue_intelligence`
   - Chart Type: *World / Country Map or Bar Chart*
   - Dimension: `customer_region`
   - Metric: `SUM(ticket_count)`
5. **CSAT Rating by Issue Category**:
   - Dataset: `v_customer_issue_intelligence`
   - Chart Type: *Bar Chart*
   - X-Axis: `category`
   - Metric: `AVG(avg_csat)`
