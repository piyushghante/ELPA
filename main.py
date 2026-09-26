import streamlit as st
import pandas as pd

from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, text


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Loan Manager",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# MOBILE-FRIENDLY CSS
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
        border-radius: 14px;
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

    .success-box {
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid rgba(0,150,0,0.25);
    }

    @media (max-width: 768px) {

        .block-container {
            padding-left: 0.7rem;
            padding-right: 0.7rem;
        }

        .amount {
            font-size: 1.4rem;
        }

    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATABASE CONNECTION
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

except Exception as error:

    st.error("Unable to connect to PostgreSQL.")

    st.exception(error)

    st.stop()


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
    # USERS TABLE
    # --------------------------------------------------------

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash TEXT,
            role VARCHAR(30) NOT NULL,
            display_name VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --------------------------------------------------------
    # LOANS TABLE
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
    # PAYMENTS TABLE
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
    # PAYMENT ALLOCATION TABLE
    # --------------------------------------------------------

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS payment_allocations (
            id SERIAL PRIMARY KEY,

            payment_id INTEGER UNIQUE NOT NULL
                REFERENCES payments(id),

            interest_amount NUMERIC(15,2)
                NOT NULL DEFAULT 0,

            principal_amount NUMERIC(15,2)
                NOT NULL DEFAULT 0,

            allocated_by VARCHAR(100) NOT NULL,

            allocated_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # --------------------------------------------------------
    # MIGRATE OLD USERS TABLE
    # --------------------------------------------------------

    # If the previous version created a "password" column,
    # remove it because passwords should now be stored as hashes.

    execute_query(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS password_hash TEXT
        """
    )


# ============================================================
# INITIALIZE DATABASE
# ============================================================

try:

    initialize_database()

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
            role,
            display_name
        FROM users
        WHERE username = :username

        AND password_hash = crypt(
            :password,
            password_hash
        )
        """,
        {
            "username": username.strip(),
            "password": password,
        },
    )

    if result.empty:

        return False

    user = result.iloc[0]

    st.session_state.logged_in = True

    st.session_state.username = user["username"]

    st.session_state.role = user["role"]

    st.session_state.display_name = user[
        "display_name"
    ]

    return True


# ============================================================
# LOGOUT
# ============================================================

def logout():

    st.session_state.logged_in = False

    st.session_state.username = None

    st.session_state.role = None

    st.session_state.display_name = None

    st.rerun()


# ============================================================
# LOGIN SCREEN
# ============================================================

if not st.session_state.logged_in:

    st.title("💰 Loan Manager")

    st.caption(
        "Simple loan and payment management"
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

            if not username or not password:

                st.warning(
                    "Please enter username and password."
                )

            elif login_user(
                username,
                password,
            ):

                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )

    st.stop()


# ============================================================
# LOAN DATA
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


# ============================================================
# PAYMENT DATA
# ============================================================

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

        ORDER BY
            p.payment_date DESC,
            p.id DESC
        """
    )


# ============================================================
# LOAN SUMMARY
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

        GROUP BY
            l.id,
            l.original_amount
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

    original = Decimal(
        str(row["original_amount"] or 0)
    )

    principal = Decimal(
        str(row["principal_paid"] or 0)
    )

    interest = Decimal(
        str(row["interest_paid"] or 0)
    )

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

    st.caption(
        f"Logged in as {st.session_state.display_name}"
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
    # CALCULATE TOTALS
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

    # --------------------------------------------------------
    # TOP METRICS
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "Outstanding Principal",
            f"₹{total_remaining:,.2f}",
        )

    with col2:

        st.metric(
            "Interest Paid",
            f"₹{total_interest:,.2f}",
        )

    st.divider()

    # --------------------------------------------------------
    # SUPERUSER DASHBOARD
    # --------------------------------------------------------

    if st.session_state.role == "superuser":

        st.subheader("Quick Actions")

        col1, col2 = st.columns(2)

        with col1:

            st.info(
                "💸 Add the amount you paid."
            )

        with col2:

            pending = len(
                payments[
                    payments["status"] == "pending"
                ]
            )

            st.metric(
                "Pending Allocations",
                pending,
            )

    # --------------------------------------------------------
    # FATHER DASHBOARD
    # --------------------------------------------------------

    else:

        pending = payments[
            payments["status"] == "pending"
        ]

        st.subheader(
            "Payments Waiting for Allocation"
        )

        st.metric(
            "Pending",
            len(pending),
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

        for _, payment in payments.head(
            5
        ).iterrows():

            if payment["status"] == "allocated":

                status_text = "✅ Allocated"

            else:

                status_text = "⏳ Pending"

            st.markdown(
                f"""
                <div class="loan-card">

                    <div class="amount">
                        ₹{float(payment["amount"]):,.2f}
                    </div>

                    <b>
                        {payment["loan_name"]}
                    </b>

                    <div class="small-text">
                        {payment["payment_date"]}
                        ·
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
            "No loans have been created yet."
        )

    else:

        for _, loan in loans.iterrows():

            summary = get_loan_summary(
                int(loan["id"])
            )

            st.markdown(
                f"""
                <div class="loan-card">

                    <h3>
                        {loan["name"]}
                    </h3>

                    <div class="small-text">
                        {loan["loan_type"].title()} Loan
                    </div>

                    <br>

                    <div class="small-text">
                        Outstanding Principal
                    </div>

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

            if loan["interest_rate"]:

                st.caption(
                    f"Interest Rate: "
                    f"{float(loan['interest_rate']):.2f}%"
                )

            if loan["notes"]:

                st.caption(
                    f"📝 {loan['notes']}"
                )

            st.divider()

    # --------------------------------------------------------
    # CREATE LOAN
    # --------------------------------------------------------

    st.subheader("➕ Create Loan")

    with st.form("create_loan_form"):

        name = st.text_input(
            "Loan Name",
            placeholder="Example: Home Loan",
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
            placeholder="Optional",
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
                        "original_amount":
                            original_amount,
                        "interest_rate":
                            interest_rate,
                        "start_date":
                            start_date,
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

    active_loans = loans[
        loans["is_active"] == True
    ]

    if active_loans.empty:

        st.warning(
            "There are no active loans."
        )

    else:

        with st.form("payment_form"):

            loan_options = {
                row["name"]:
                int(row["id"])
                for _, row
                in active_loans.iterrows()
            }

            selected_loan = st.selectbox(
                "Loan",
                list(
                    loan_options.keys()
                ),
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
                            "payment_date":
                                payment_date,
                            "paid_by":
                                st.session_state.username,
                            "note": note,
                        },
                    )

                    st.success(
                        f"₹{amount:,.2f} payment recorded."
                    )

                    st.info(
                        "Your father can now allocate this payment."
                    )

                    st.rerun()


# ============================================================
# PENDING PAYMENTS
# ============================================================

elif page == "Pending Payments":

    st.title("⏳ Pending Payments")

    st.caption(
        "Allocate received payments between "
        "interest and principal."
    )

    payments = get_payments()

    pending = payments[
        payments["status"] == "pending"
    ]

    if pending.empty:

        st.success(
            "No pending payments."
        )

    else:

        for _, payment in pending.iterrows():

            payment_amount = float(
                payment["amount"]
            )

            st.markdown(
                f"""
                <div class="loan-card">

                    <div class="amount">
                        ₹{payment_amount:,.2f}
                    </div>

                    <b>
                        {payment["loan_name"]}
                    </b>

                    <div class="small-text">
                        Paid on
                        {payment["payment_date"]}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
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
                )

                principal = st.number_input(
                    "Principal",
                    min_value=0.0,
                    max_value=payment_amount,
                    value=0.0,
                    step=100.0,
                )

                total = (
                    interest +
                    principal
                )

                remaining = (
                    payment_amount -
                    total
                )

                if remaining > 0:

                    st.caption(
                        f"Remaining to allocate: "
                        f"₹{remaining:,.2f}"
                    )

                elif remaining < 0:

                    st.error(
                        "Allocation exceeds payment."
                    )

                else:

                    st.success(
                        "Fully allocated."
                    )

                submitted = st.form_submit_button(
                    "Confirm Allocation",
                    type="primary",
                    width="stretch",
                )

                if submitted:

                    if abs(
                        total -
                        payment_amount
                    ) > 0.01:

                        st.error(
                            "Interest + Principal "
                            "must equal the payment amount."
                        )

                    else:

                        execute_query(
                            """
                            INSERT INTO
                            payment_allocations (
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
                                "payment_id":
                                    int(
                                        payment["id"]
                                    ),
                                "interest":
                                    interest,
                                "principal":
                                    principal,
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
                                    int(
                                        payment["id"]
                                    )
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

                    <b>
                        {payment["loan_name"]}
                    </b>

                    <div class="small-text">
                        {payment["payment_date"]}
                        ·
                        {status}
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
                        f"Allocated by: "
                        f"{payment['allocated_by']}"
                    )

            if payment["note"]:

                st.caption(
                    f"📝 {payment['note']}"
                )

            st.divider()


# ============================================================
# LOANS - FATHER VIEW
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

                    <h3>
                        {loan["name"]}
                    </h3>

                    <div class="small-text">
                        {loan["loan_type"].title()} Loan
                    </div>

                    <br>

                    <div class="small-text">
                        Remaining Principal
                    </div>

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
