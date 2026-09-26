import streamlit as st
import pandas as pd

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Loan Manager",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CUSTOM CSS - MOBILE FRIENDLY
# ============================================================

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
            max-width: 1200px;
        }

        .loan-card {
            padding: 1rem;
            border-radius: 12px;
            border: 1px solid rgba(128,128,128,0.25);
            margin-bottom: 1rem;
        }

        .amount {
            font-size: 1.7rem;
            font-weight: 700;
        }

        .small-text {
            font-size: 0.85rem;
            opacity: 0.7;
        }

        div[data-testid="stMetric"] {
            padding: 0.5rem;
        }

        @media (max-width: 768px) {
            .block-container {
                padding-left: 0.7rem;
                padding-right: 0.7rem;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATABASE
# ============================================================

@st.cache_resource
def get_database_engine():
    database_url = st.secrets["DATABASE_URL"]

    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
    )


try:
    engine = get_database_engine()
    database_available = True
except Exception as error:
    database_available = False
    st.error("Unable to initialize database connection.")
    st.exception(error)


# ============================================================
# DATABASE HELPERS
# ============================================================

def execute_query(query, params=None):
    with engine.begin() as connection:
        return connection.execute(
            text(query),
            params or {},
        )


def read_query(query, params=None):
    with engine.connect() as connection:
        return pd.read_sql(
            text(query),
            connection,
            params=params or {},
        )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database():

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(30) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --------------------------------------------------------
    # LOANS
    # --------------------------------------------------------

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS loans (
            id SERIAL PRIMARY KEY,

            name VARCHAR(150) NOT NULL,

            loan_type VARCHAR(30) NOT NULL,

            original_amount NUMERIC(15,2) NOT NULL,

            interest_rate NUMERIC(8,4) DEFAULT 0,

            start_date DATE NOT NULL,

            notes TEXT,

            is_active BOOLEAN DEFAULT TRUE,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --------------------------------------------------------
    # PAYMENTS
    # --------------------------------------------------------

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,

            loan_id INTEGER NOT NULL
                REFERENCES loans(id),

            amount NUMERIC(15,2) NOT NULL,

            payment_date DATE NOT NULL,

            paid_by VARCHAR(100) NOT NULL,

            status VARCHAR(30) DEFAULT 'pending',

            note TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --------------------------------------------------------
    # PAYMENT ALLOCATIONS
    # --------------------------------------------------------

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS payment_allocations (
            id SERIAL PRIMARY KEY,

            payment_id INTEGER UNIQUE NOT NULL
                REFERENCES payments(id),

            interest_amount NUMERIC(15,2) NOT NULL DEFAULT 0,

            principal_amount NUMERIC(15,2) NOT NULL DEFAULT 0,

            allocated_by VARCHAR(100) NOT NULL,

            allocated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


# ============================================================
# DEFAULT USERS
# ============================================================

def create_default_users():

    users = [
        {
            "username": "superuser",
            "password": "CHANGE_THIS_PASSWORD",
            "role": "superuser",
            "display_name": "Me",
        },
        {
            "username": "home",
            "password": "CHANGE_THIS_PASSWORD",
            "role": "home",
            "display_name": "Father",
        },
    ]

    for user in users:

        existing = read_query(
            """
            SELECT id
            FROM users
            WHERE username = :username
            """,
            {
                "username": user["username"]
            },
        )

        if existing.empty:

            execute_query(
                """
                INSERT INTO users (
                    username,
                    password,
                    role,
                    display_name
                )
                VALUES (
                    :username,
                    :password,
                    :role,
                    :display_name
                )
                """,
                user,
            )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

if database_available:

    try:
        initialize_database()
        create_default_users()

    except Exception as error:
        st.error("Database initialization failed.")
        st.exception(error)
        st.stop()


# ============================================================
# SESSION STATE
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = None

if "role" not in st.session_state:
    st.session_state.role = None

if "display_name" not in st.session_state:
    st.session_state.display_name = None


# ============================================================
# LOGIN
# ============================================================

def login_user(username, password):

    result = read_query(
        """
        SELECT
            username,
            password,
            role,
            display_name
        FROM users
        WHERE username = :username
        """,
        {
            "username": username
        },
    )

    if result.empty:
        return False

    user = result.iloc[0]

    if password != user["password"]:
        return False

    st.session_state.logged_in = True
    st.session_state.username = user["username"]
    st.session_state.role = user["role"]
    st.session_state.display_name = user["display_name"]

    return True


def logout():

    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.display_name = None

    st.rerun()


# ============================================================
# LOGIN PAGE
# ============================================================

if not st.session_state.logged_in:

    st.title("💰 Loan Manager")

    st.caption(
        "Simple loan and payment tracking"
    )

    st.write("")

    with st.form("login_form"):

        username = st.text_input(
            "Username",
            placeholder="Enter username",
        )

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter password",
        )

        login_clicked = st.form_submit_button(
            "Login",
            type="primary",
            width="stretch",
        )

        if login_clicked:

            if login_user(username, password):

                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )

    st.stop()


# ============================================================
# COMMON DATA
# ============================================================

def get_loans():

    return read_query(
        """
        SELECT
            id,
            name,
            loan_type,
            original_amount,
            interest_rate,
            start_date,
            notes,
            is_active
        FROM loans
        ORDER BY created_at DESC
        """
    )


def get_payments():

    return read_query(
        """
        SELECT
            p.id,
            p.loan_id,
            l.name AS loan_name,
            p.amount,
            p.payment_date,
            p.paid_by,
            p.status,
            p.note,

            COALESCE(
                pa.interest_amount,
                0
            ) AS interest_amount,

            COALESCE(
                pa.principal_amount,
                0
            ) AS principal_amount,

            pa.allocated_by,
            pa.allocated_at

        FROM payments p

        JOIN loans l
            ON p.loan_id = l.id

        LEFT JOIN payment_allocations pa
            ON p.id = pa.payment_id

        ORDER BY p.payment_date DESC, p.id DESC
        """
    )


# ============================================================
# CALCULATIONS
# ============================================================

def get_loan_summary(loan_id):

    result = read_query(
        """
        SELECT

            l.original_amount,

            COALESCE(
                SUM(pa.principal_amount),
                0
            ) AS principal_paid,

            COALESCE(
                SUM(pa.interest_amount),
                0
            ) AS interest_paid

        FROM loans l

        LEFT JOIN payments p
            ON l.id = p.loan_id

        LEFT JOIN payment_allocations pa
            ON p.id = pa.payment_id

        WHERE l.id = :loan_id

        GROUP BY l.id, l.original_amount
        """,
        {
            "loan_id": loan_id
        },
    )

    if result.empty:
        return {
            "original": Decimal("0"),
            "principal": Decimal("0"),
            "interest": Decimal("0"),
            "remaining": Decimal("0"),
        }

    row = result.iloc[0]

    original = Decimal(str(row["original_amount"] or 0))
    principal = Decimal(str(row["principal_paid"] or 0))
    interest = Decimal(str(row["interest_paid"] or 0))

    remaining = max(
        original - principal,
        Decimal("0"),
    )

    return {
        "original": original,
        "principal": principal,
        "interest": interest,
        "remaining": remaining,
    }


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("💰 Loan Manager")

    st.write(
        f"Welcome, **{st.session_state.display_name}**"
    )

    st.divider()

    if st.session_state.role == "superuser":

        page = st.radio(
            "Menu",
            [
                "Dashboard",
                "My Loans",
                "Add Payment",
                "Payment History",
            ],
        )

    else:

        page = st.radio(
            "Menu",
            [
                "Dashboard",
                "Pending Payments",
                "Payment History",
                "Loans",
            ],
        )

    st.divider()

    if st.button(
        "Logout",
        width="stretch",
    ):
        logout()


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    st.title("🏠 Dashboard")

    loans = get_loans()
    payments = get_payments()

    # --------------------------------------------------------
    # TOTALS
    # --------------------------------------------------------

    total_original = Decimal("0")
    total_principal = Decimal("0")
    total_interest = Decimal("0")

    for loan_id in loans["id"].tolist():

        summary = get_loan_summary(
            int(loan_id)
        )

        total_original += summary["original"]
        total_principal += summary["principal"]
        total_interest += summary["interest"]

    total_remaining = max(
        total_original - total_principal,
        Decimal("0"),
    )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Outstanding Principal",
            f"₹{total_remaining:,.2f}",
        )

    with col2:

        st.metric(
            "Total Interest Paid",
            f"₹{total_interest:,.2f}",
        )

    st.divider()

    # --------------------------------------------------------
    # QUICK ACTIONS
    # --------------------------------------------------------

    if st.session_state.role == "superuser":

        st.subheader("Quick Actions")

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "💸 Add Payment",
                width="stretch",
                type="primary",
            ):
                st.session_state.dashboard_action = "payment"

        with col2:

            st.info(
                "Record the amount you paid."
            )

    else:

        pending_count = len(
            payments[
                payments["status"] == "pending"
            ]
        )

        st.subheader("Pending Payments")

        st.metric(
            "Waiting for Allocation",
            pending_count,
        )

    # --------------------------------------------------------
    # RECENT PAYMENTS
    # --------------------------------------------------------

    st.subheader("Recent Payments")

    if payments.empty:

        st.info(
            "No payments recorded yet."
        )

    else:

        recent = payments.head(5)

        for _, payment in recent.iterrows():

            status = payment["status"]

            if status == "allocated":
                status_text = "✅ Allocated"
            else:
                status_text = "⏳ Pending"

            st.markdown(
                f"""
                <div class="loan-card">

                <div class="amount">
                ₹{float(payment["amount"]):,.2f}
                </div>

                <b>{payment["loan_name"]}</b>

                <div class="small-text">
                {payment["payment_date"]} ·
                {status_text}
                </div>

                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# MY LOANS
# ============================================================

elif page == "My Loans":

    st.title("💰 My Loans")

    loans = get_loans()

    if loans.empty:

        st.info(
            "No loans have been added yet."
        )

    else:

        for _, loan in loans.iterrows():

            summary = get_loan_summary(
                int(loan["id"])
            )

            st.markdown(
                f"""
                <div class="loan-card">

                <h3>{loan["name"]}</h3>

                <div class="small-text">
                {loan["loan_type"].title()}
                </div>

                <br>

                <b>Outstanding</b>

                <div class="amount">
                ₹{summary["remaining"]:,.2f}
                </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Original",
                    f"₹{summary['original']:,.0f}",
                )

            with col2:
                st.metric(
                    "Principal Paid",
                    f"₹{summary['principal']:,.0f}",
                )

            with col3:
                st.metric(
                    "Interest Paid",
                    f"₹{summary['interest']:,.0f}",
                )

            if loan["notes"]:
                st.caption(
                    f"📝 {loan['notes']}"
                )

            st.divider()

        # ----------------------------------------------------
        # ADD LOAN
        # ----------------------------------------------------

        st.subheader("➕ Add Loan")

        with st.form("add_loan_form"):

            name = st.text_input(
                "Loan Name",
                placeholder="e.g. Home Goal Loan",
            )

            loan_type = st.selectbox(
                "Loan Type",
                [
                    "goal",
                    "fixed",
                ],
            )

            original_amount = st.number_input(
                "Original Principal Amount",
                min_value=0.0,
                step=1000.0,
            )

            interest_rate = st.number_input(
                "Interest Rate (%)",
                min_value=0.0,
                step=0.1,
            )

            start_date = st.date_input(
                "Start Date",
                value=date.today(),
            )

            notes = st.text_area(
                "Notes",
                placeholder="Optional notes",
            )

            submitted = st.form_submit_button(
                "Create Loan",
                type="primary",
                width="stretch",
            )

            if submitted:

                if not name.strip():

                    st.error(
                        "Loan name is required."
                    )

                elif original_amount <= 0:

                    st.error(
                        "Original amount must be greater than zero."
                    )

                else:

                    execute_query(
                        """
                        INSERT INTO loans (
                            name,
                            loan_type,
                            original_amount,
                            interest_rate,
                            start_date,
                            notes
                        )
                        VALUES (
                            :name,
                            :loan_type,
                            :original_amount,
                            :interest_rate,
                            :start_date,
                            :notes
                        )
                        """,
                        {
                            "name": name.strip(),
                            "loan_type": loan_type,
                            "original_amount": original_amount,
                            "interest_rate": interest_rate,
                            "start_date": start_date,
                            "notes": notes,
                        },
                    )

                    st.success(
                        "Loan created successfully."
                    )

                    st.rerun()


# ============================================================
# ADD PAYMENT
# ============================================================

elif page == "Add Payment":

    st.title("💸 Add Payment")

    st.caption(
        "Record money you paid to your father."
    )

    loans = get_loans()

    if loans.empty:

        st.warning(
            "Create a loan first."
        )

    else:

        with st.form("payment_form"):

            loan_options = {
                f"{row['name']} — ₹{float(row['original_amount']):,.0f}":
                int(row["id"])
                for _, row in loans.iterrows()
                if row["is_active"]
            }

            selected_loan = st.selectbox(
                "Loan",
                list(loan_options.keys()),
            )

            amount = st.number_input(
                "Amount Paid",
                min_value=0.0,
                step=500.0,
            )

            payment_date = st.date_input(
                "Payment Date",
                value=date.today(),
            )

            note = st.text_area(
                "Note",
                placeholder="Optional note",
            )

            submitted = st.form_submit_button(
                "Record Payment",
                type="primary",
                width="stretch",
            )

            if submitted:

                if amount <= 0:

                    st.error(
                        "Payment amount must be greater than zero."
                    )

                else:

                    loan_id = loan_options[
                        selected_loan
                    ]

                    execute_query(
                        """
                        INSERT INTO payments (
                            loan_id,
                            amount,
                            payment_date,
                            paid_by,
                            status,
                            note
                        )
                        VALUES (
                            :loan_id,
                            :amount,
                            :payment_date,
                            :paid_by,
                            'pending',
                            :note
                        )
                        """,
                        {
                            "loan_id": loan_id,
                            "amount": amount,
                            "payment_date": payment_date,
                            "paid_by": st.session_state.username,
                            "note": note,
                        },
                    )

                    st.success(
                        f"₹{amount:,.2f} payment recorded."
                    )

                    st.info(
                        "Your father can now allocate this payment between interest and principal."
                    )

                    st.rerun()


# ============================================================
# PENDING PAYMENTS - FATHER
# ============================================================

elif page == "Pending Payments":

    st.title("⏳ Pending Payments")

    st.caption(
        "Allocate each received payment between interest and principal."
    )

    payments = get_payments()

    pending = payments[
        payments["status"] == "pending"
    ]

    if pending.empty:

        st.success(
            "No payments are waiting for allocation."
        )

    else:

        for _, payment in pending.iterrows():

            st.markdown(
                f"""
                <div class="loan-card">

                <h3>₹{float(payment["amount"]):,.2f}</h3>

                <b>{payment["loan_name"]}</b>

                <div class="small-text">
                Paid on {payment["payment_date"]}
                </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            payment_amount = float(
                payment["amount"]
            )

            with st.form(
                f"allocation_{payment['id']}"
            ):

                interest = st.number_input(
                    "Interest",
                    min_value=0.0,
                    max_value=payment_amount,
                    value=0.0,
                    step=100.0,
                    key=f"interest_{payment['id']}",
                )

                principal = st.number_input(
                    "Principal",
                    min_value=0.0,
                    max_value=payment_amount,
                    value=0.0,
                    step=100.0,
                    key=f"principal_{payment['id']}",
                )

                total = interest + principal

                st.write(
                    f"Allocated: ₹{total:,.2f} / ₹{payment_amount:,.2f}"
                )

                submitted = st.form_submit_button(
                    "Confirm Allocation",
                    type="primary",
                    width="stretch",
                )

                if submitted:

                    if abs(
                        total - payment_amount
                    ) > 0.01:

                        st.error(
                            f"Interest + Principal must equal ₹{payment_amount:,.2f}"
                        )

                    else:

                        execute_query(
                            """
                            INSERT INTO payment_allocations (
                                payment_id,
                                interest_amount,
                                principal_amount,
                                allocated_by
                            )
                            VALUES (
                                :payment_id,
                                :interest,
                                :principal,
                                :allocated_by
                            )
                            """,
                            {
                                "payment_id": int(payment["id"]),
                                "interest": interest,
                                "principal": principal,
                                "allocated_by":
                                    st.session_state.username,
                            },
                        )

                        execute_query(
                            """
                            UPDATE payments
                            SET status = 'allocated'
                            WHERE id = :payment_id
                            """,
                            {
                                "payment_id":
                                    int(payment["id"])
                            },
                        )

                        st.success(
                            "Payment allocation saved."
                        )

                        st.rerun()

            st.divider()


# ============================================================
# PAYMENT HISTORY
# ============================================================

elif page == "Payment History":

    st.title("📜 Payment History")

    payments = get_payments()

    if payments.empty:

        st.info(
            "No payments recorded yet."
        )

    else:

        for _, payment in payments.iterrows():

            if payment["status"] == "allocated":

                status = "✅ Allocated"

            else:

                status = "⏳ Pending"

            st.markdown(
                f"""
                <div class="loan-card">

                <div class="amount">
                ₹{float(payment["amount"]):,.2f}
                </div>

                <b>{payment["loan_name"]}</b>

                <div class="small-text">
                {payment["payment_date"]} · {status}
                </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            if payment["status"] == "allocated":

                col1, col2 = st.columns(2)

                with col1:

                    st.metric(
                        "Interest",
                        f"₹{float(payment['interest_amount']):,.2f}",
                    )

                with col2:

                    st.metric(
                        "Principal",
                        f"₹{float(payment['principal_amount']):,.2f}",
                    )

                if payment["allocated_by"]:

                    st.caption(
                        f"Allocated by: {payment['allocated_by']}"
                    )

            if payment["note"]:

                st.caption(
                    f"📝 {payment['note']}"
                )

            st.divider()


# ============================================================
# LOANS - FATHER
# ============================================================

elif page == "Loans":

    st.title("💰 Loans")

    loans = get_loans()

    if loans.empty:

        st.info(
            "No loans available."
        )

    else:

        for _, loan in loans.iterrows():

            summary = get_loan_summary(
                int(loan["id"])
            )

            st.markdown(
                f"""
                <div class="loan-card">

                <h3>{loan["name"]}</h3>

                <div class="small-text">
                {loan["loan_type"].title()} Loan
                </div>

                <br>

                <b>Remaining Principal</b>

                <div class="amount">
                ₹{summary["remaining"]:,.2f}
                </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            col1, col2 = st.columns(2)

            with col1:

                st.metric(
                    "Principal Paid",
                    f"₹{summary['principal']:,.2f}",
                )

            with col2:

                st.metric(
                    "Interest Paid",
                    f"₹{summary['interest']:,.2f}",
                )

            st.divider()
