import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
import pandas as pd
from config import Config

class ManagerInsightsEngine:
    def __init__(self, db_uri=None):
        self.db_uri = db_uri or Config.SQLALCHEMY_DATABASE_URI
        self.engine = create_engine(self.db_uri)

    def generate_insights(self):
        insights = []
        with self.engine.connect() as conn:
            # 1. Top Category Volume & SLA Impact Analysis
            cat_query = text("""
                SELECT 
                    category,
                    COUNT(*) AS total_count,
                    COUNT(*) FILTER (WHERE is_sla_breached = TRUE) AS breached_count,
                    ROUND(AVG(resolution_hours), 2) AS avg_res_hours,
                    ROUND(AVG(csat) FILTER (WHERE csat > 0), 2) AS avg_csat
                FROM fact_tickets
                GROUP BY category
                ORDER BY total_count DESC
                LIMIT 3;
            """)
            top_cats = pd.read_sql(cat_query, conn)
            
            if not top_cats.empty:
                top_cat = top_cats.iloc[0]
                insight_1 = {
                    "type": "Category Alert",
                    "title": f"High Volume Trend: {top_cat['category']}",
                    "evidence": (
                        f"'{top_cat['category']}' is the most frequent issue, representing {top_cat['total_count']} tickets. "
                        f"Average resolution time is currently {top_cat['avg_res_hours']} hours with {top_cat['breached_count']} SLA breaches "
                        f"and an average CSAT of {top_cat['avg_csat']}/5.0."
                    ),
                    "impact": f"Resolution SLA breaches in this category account for {top_cat['breached_count']} customer friction points.",
                    "recommended_action": f"Audit the {top_cat['category']} workflow and allocate supplementary support capacity to the primary team."
                }
                insights.append(insight_1)

            # 2. SLA Breach Risk High-Risk Queue Alert
            risk_query = text("""
                SELECT 
                    COUNT(*) AS high_risk_count,
                    COUNT(*) FILTER (WHERE sla_risk_category = 'Breached') AS breached_count
                FROM fact_tickets
                WHERE status IN ('Open', 'In Progress');
            """)
            risk_df = pd.read_sql(risk_query, conn)
            if not risk_df.empty:
                h_count = risk_df.iloc[0]['high_risk_count']
                b_count = risk_df.iloc[0]['breached_count']
                insight_2 = {
                    "type": "SLA Breach Queue",
                    "title": "Active Backlog & SLA Breach Risk",
                    "evidence": f"There are currently {h_count} active open tickets in the support queue. {b_count} open tickets have exceeded their SLA target limit.",
                    "impact": "Unresolved backlog risks reducing overall CSAT and breaching enterprise SLA contracts.",
                    "recommended_action": "Prioritize open tickets with SLA Risk Score > 0.80 immediately in the Agent Performance view."
                }
                insights.append(insight_2)

            # 3. Agent SLA Compliance Benchmark
            agent_query = text("""
                SELECT 
                    team,
                    ROUND(AVG(sla_compliance_pct), 2) AS team_sla_pct
                FROM v_agent_performance
                GROUP BY team
                ORDER BY team_sla_pct ASC
                LIMIT 1;
            """)
            agent_df = pd.read_sql(agent_query, conn)
            if not agent_df.empty:
                low_team = agent_df.iloc[0]
                insight_3 = {
                    "type": "Team Operational Efficiency",
                    "title": f"Team SLA Benchmark: {low_team['team']}",
                    "evidence": f"The '{low_team['team']}' team recorded the lowest overall SLA compliance rate at {low_team['team_sla_pct']}% across active tickets.",
                    "impact": "Team-level bottlenecks are extending ticket lifecycle durations.",
                    "recommended_action": f"Review workload distribution for '{low_team['team']}' agents and automate common troubleshooting steps."
                }
                insights.append(insight_3)

        return insights
