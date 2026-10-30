import datetime
import uuid
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from sqlalchemy import create_engine, text, event
from config import Config

logger = logging.getLogger("IntakeBlueprint")

intake_bp = Blueprint("intake", __name__, template_folder="../templates")

def get_engine():
    """Get the SQLAlchemy engine from the Flask app context or create a new one."""
    if current_app and "ENGINE" in current_app.config and current_app.config["ENGINE"] is not None:
        return current_app.config["ENGINE"]
    return create_engine(Config.SQLALCHEMY_DATABASE_URI)

def ensure_ops_schema(engine):
    """Ensure that the ops schema and ops.tickets table exist."""
    try:
        is_sqlite = "sqlite" in str(engine.url)
        if is_sqlite:
            # For SQLite, attach an in-memory or file-backed database named 'ops'
            @event.listens_for(engine, "connect")
            def _attach_ops_db(dbapi_con, con_record):
                try:
                    dbapi_con.execute("ATTACH DATABASE '' AS ops")
                except Exception:
                    pass

            with engine.begin() as conn:
                try:
                    conn.execute(text("ATTACH DATABASE '' AS ops"))
                except Exception:
                    pass
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS ops.tickets (
                        ticket_id VARCHAR(50) PRIMARY KEY,
                        customer_id VARCHAR(50),
                        agent_id VARCHAR(50),
                        product_id VARCHAR(50),
                        category VARCHAR(100) NOT NULL,
                        priority VARCHAR(50) NOT NULL,
                        channel VARCHAR(50) NOT NULL,
                        status VARCHAR(50) NOT NULL DEFAULT 'Open',
                        notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
        else:
            with engine.begin() as conn:
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS ops;"))
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS ops.tickets (
                        ticket_id VARCHAR(50) PRIMARY KEY,
                        customer_id VARCHAR(50),
                        agent_id VARCHAR(50),
                        product_id VARCHAR(50),
                        category VARCHAR(100) NOT NULL,
                        priority VARCHAR(50) NOT NULL,
                        channel VARCHAR(50) NOT NULL,
                        status VARCHAR(50) NOT NULL DEFAULT 'Open',
                        notes TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """))
    except Exception as e:
        logger.warning(f"Could not automatically ensure ops schema: {e}")

@intake_bp.route("/", methods=["GET"])
@intake_bp.route("", methods=["GET"])
def intake():
    """Ticket submission form and recent intake queue view."""
    engine = get_engine()
    ensure_ops_schema(engine)
    recent_tickets = []
    
    try:
        query = text("""
            SELECT ticket_id, customer_id, agent_id, product_id, category, 
                   priority, channel, status, notes, created_at, updated_at
            FROM ops.tickets
            ORDER BY created_at DESC
            LIMIT 50
        """)
        with engine.connect() as conn:
            result = conn.execute(query)
            recent_tickets = [dict(row._mapping) for row in result]
    except Exception as e:
        logger.warning(f"Unable to query ops.tickets: {e}")
        recent_tickets = []

    return render_template("intake.html", recent_tickets=recent_tickets)

@intake_bp.route("/submit", methods=["POST"])
def submit():
    """Form handler: Inserts a new ticket into ops.tickets using parameterized SQL."""
    engine = get_engine()
    ensure_ops_schema(engine)

    # Extract form inputs
    customer_id = (request.form.get("customer_id") or "").strip()
    product_id = (request.form.get("product_id") or "PRD-01").strip()
    category = (request.form.get("category") or "").strip()
    priority = (request.form.get("priority") or "Medium").strip()
    channel = (request.form.get("channel") or "Web Portal").strip()
    agent_id = (request.form.get("agent_id") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    if not customer_id or not category or not priority:
        flash("Customer ID, Category, and Priority are required.", "danger")
        return redirect(url_for("intake.intake"))

    # Generate unique ticket ID
    ticket_id = f"TKT-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
    now = datetime.datetime.now(datetime.timezone.utc)

    # Parameterized SQL write
    insert_sql = text("""
        INSERT INTO ops.tickets (
            ticket_id, customer_id, agent_id, product_id, category,
            priority, channel, status, notes, created_at, updated_at
        ) VALUES (
            :ticket_id, :customer_id, :agent_id, :product_id, :category,
            :priority, :channel, :status, :notes, :created_at, :updated_at
        )
    """)

    params = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "agent_id": agent_id,
        "product_id": product_id,
        "category": category,
        "priority": priority,
        "channel": channel,
        "status": "Open",
        "notes": notes,
        "created_at": now,
        "updated_at": now
    }

    try:
        with engine.begin() as conn:
            conn.execute(insert_sql, params)
        flash(f"Ticket {ticket_id} submitted successfully to ops.tickets!", "success")
    except Exception as e:
        logger.error(f"Failed to insert ticket: {e}")
        flash(f"Database error creating ticket: {str(e)}", "danger")

    return redirect(url_for("intake.intake"))

@intake_bp.route("/tickets/<ticket_id>/status", methods=["POST"])
@intake_bp.route("/tickets/<ticket_id>", methods=["POST", "PATCH"])
def update_ticket_status(ticket_id):
    """
    Update ticket status in ops.tickets using parameterized SQL.
    Supports POST from forms as well as JSON payloads.
    """
    engine = get_engine()
    ensure_ops_schema(engine)

    # Extract status from form data or JSON body
    if request.is_json:
        data = request.get_json(silent=True) or {}
        new_status = data.get("status")
    else:
        new_status = request.form.get("status")

    if not new_status:
        if request.is_json:
            return jsonify({"error": "Missing 'status' in request"}), 400
        flash("Status value is required to update ticket.", "warning")
        return redirect(request.referrer or url_for("intake.intake"))

    now = datetime.datetime.now(datetime.timezone.utc)

    # Parameterized SQL write
    update_sql = text("""
        UPDATE ops.tickets
        SET status = :status, updated_at = :updated_at
        WHERE ticket_id = :ticket_id
    """)

    params = {
        "status": new_status,
        "updated_at": now,
        "ticket_id": ticket_id
    }

    try:
        with engine.begin() as conn:
            result = conn.execute(update_sql, params)
            if result.rowcount == 0:
                if request.is_json:
                    return jsonify({"error": f"Ticket {ticket_id} not found"}), 404
                flash(f"Ticket {ticket_id} not found in ops.tickets.", "warning")
            else:
                if request.is_json:
                    return jsonify({"success": True, "ticket_id": ticket_id, "status": new_status}), 200
                flash(f"Status for {ticket_id} updated to {new_status}.", "success")

    except Exception as e:
        logger.error(f"Failed to update ticket {ticket_id}: {e}")
        if request.is_json:
            return jsonify({"error": str(e)}), 500
        flash(f"Database error updating status: {str(e)}", "danger")

    return redirect(request.referrer or url_for("intake.intake"))
