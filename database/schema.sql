-- SupportIQ Analytics Store Schema Definition
-- Database: supportiq_analytics

CREATE TABLE IF NOT EXISTS dim_agents (
    agent_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    team VARCHAR(100) NOT NULL,
    region VARCHAR(50) NOT NULL,
    joining_date DATE,
    manager VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS dim_customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_segment VARCHAR(50) NOT NULL,
    region VARCHAR(50) NOT NULL,
    signup_date DATE,
    plan VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS dim_products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    product_category VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_tickets (
    ticket_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES dim_customers(customer_id),
    agent_id VARCHAR(50) REFERENCES dim_agents(agent_id),
    product_id VARCHAR(50) REFERENCES dim_products(product_id),
    category VARCHAR(100) NOT NULL,
    priority VARCHAR(50) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    first_response_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    sla_target_hours NUMERIC(10,2) NOT NULL,
    first_response_hours NUMERIC(10,2),
    resolution_hours NUMERIC(10,2),
    is_sla_breached BOOLEAN DEFAULT FALSE,
    sla_risk_score NUMERIC(5,4),
    sla_risk_category VARCHAR(50),
    csat NUMERIC(3,2),
    customer_region VARCHAR(50) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sla_risk_log (
    log_id SERIAL PRIMARY KEY,
    ticket_id VARCHAR(50) REFERENCES fact_tickets(ticket_id),
    elapsed_hours NUMERIC(10,2) NOT NULL,
    sla_target_hours NUMERIC(10,2) NOT NULL,
    sla_risk_score NUMERIC(5,4) NOT NULL,
    sla_risk_category VARCHAR(50) NOT NULL,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_fact_tickets_status ON fact_tickets(status);
CREATE INDEX IF NOT EXISTS idx_fact_tickets_priority ON fact_tickets(priority);
CREATE INDEX IF NOT EXISTS idx_fact_tickets_category ON fact_tickets(category);
CREATE INDEX IF NOT EXISTS idx_fact_tickets_created_at ON fact_tickets(created_at);
CREATE INDEX IF NOT EXISTS idx_fact_tickets_agent ON fact_tickets(agent_id);
CREATE INDEX IF NOT EXISTS idx_fact_tickets_customer ON fact_tickets(customer_id);

-- SQL Analytical Views for Apache Superset

-- 1. Executive KPIs Summary View
CREATE OR REPLACE VIEW v_executive_kpis AS
SELECT
    COUNT(*) AS total_tickets,
    COUNT(*) FILTER (WHERE status IN ('Open', 'In Progress')) AS open_tickets,
    COUNT(*) FILTER (WHERE status IN ('Resolved', 'Closed')) AS resolved_tickets,
    ROUND(
        (COUNT(*) FILTER (WHERE status IN ('Resolved', 'Closed') AND is_sla_breached = FALSE)::NUMERIC / 
        NULLIF(COUNT(*) FILTER (WHERE status IN ('Resolved', 'Closed')), 0)) * 100, 2
    ) AS sla_compliance_pct,
    ROUND(AVG(resolution_hours) FILTER (WHERE status IN ('Resolved', 'Closed')), 2) AS avg_resolution_hours,
    ROUND(AVG(csat) FILTER (WHERE csat > 0), 2) AS avg_csat,
    ROUND(
        (COUNT(*) FILTER (WHERE status IN ('Open', 'In Progress'))::NUMERIC / NULLIF(COUNT(*), 0)) * 100, 2
    ) AS unresolved_backlog_pct
FROM fact_tickets;

-- 2. Agent Performance View
CREATE OR REPLACE VIEW v_agent_performance AS
SELECT
    a.agent_id,
    a.name AS agent_name,
    a.team,
    a.region,
    COUNT(t.ticket_id) AS total_handled,
    COUNT(t.ticket_id) FILTER (WHERE t.status IN ('Resolved', 'Closed')) AS resolved_count,
    COUNT(t.ticket_id) FILTER (WHERE t.status IN ('Open', 'In Progress')) AS open_backlog,
    ROUND(AVG(t.resolution_hours) FILTER (WHERE t.status IN ('Resolved', 'Closed')), 2) AS avg_resolution_hours,
    ROUND(
        (COUNT(*) FILTER (WHERE t.status IN ('Resolved', 'Closed') AND t.is_sla_breached = FALSE)::NUMERIC /
        NULLIF(COUNT(*) FILTER (WHERE t.status IN ('Resolved', 'Closed')), 0)) * 100, 2
    ) AS sla_compliance_pct,
    ROUND(AVG(t.csat) FILTER (WHERE t.csat > 0), 2) AS avg_csat
FROM dim_agents a
LEFT JOIN fact_tickets t ON a.agent_id = t.agent_id
GROUP BY a.agent_id, a.name, a.team, a.region;

-- 3. SLA Risk Queue View (For Open / In-Progress Tickets)
CREATE OR REPLACE VIEW v_sla_risk_queue AS
SELECT
    t.ticket_id,
    t.customer_id,
    c.customer_segment,
    t.priority,
    t.category,
    t.agent_id,
    a.name AS agent_name,
    t.status,
    t.created_at,
    t.sla_target_hours,
    t.sla_risk_score,
    t.sla_risk_category
FROM fact_tickets t
LEFT JOIN dim_customers c ON t.customer_id = c.customer_id
LEFT JOIN dim_agents a ON t.agent_id = a.agent_id
WHERE t.status IN ('Open', 'In Progress')
ORDER BY t.sla_risk_score DESC;

-- 4. Customer & Issue Intelligence View
CREATE OR REPLACE VIEW v_customer_issue_intelligence AS
SELECT
    t.category,
    p.product_name,
    c.customer_segment,
    t.customer_region,
    COUNT(t.ticket_id) AS ticket_count,
    ROUND(AVG(t.resolution_hours) FILTER (WHERE t.status IN ('Resolved', 'Closed')), 2) AS avg_resolution_hours,
    ROUND(AVG(t.csat) FILTER (WHERE t.csat > 0), 2) AS avg_csat,
    COUNT(DISTINCT t.customer_id) AS unique_customers
FROM fact_tickets t
LEFT JOIN dim_products p ON t.product_id = p.product_id
LEFT JOIN dim_customers c ON t.customer_id = c.customer_id
GROUP BY t.category, p.product_name, c.customer_segment, t.customer_region;
