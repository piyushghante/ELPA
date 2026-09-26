import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Loan Management",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# Database connection
# --------------------------------------------------

@st.cache_resource
def get_database_engine():
    database_url = st.secrets["DATABASE_URL"]

    return create_engine(
        database_url,
        pool_pre_ping=True,
    )


engine = get_database_engine()


# --------------------------------------------------
# Database helper
# --------------------------------------------------

def execute_query(query: str, params: dict | None = None):
    with engine.begin() as connection:
        result = connection.execute(
            text(query),
            params or {},
        )

        return result


def read_query(query: str, params: dict | None = None):
    with engine.connect() as connection:
        return pd.read_sql(
            text(query),
            connection,
            params=params or {},
        )


# --------------------------------------------------
# Database initialization
# --------------------------------------------------

def initialize_database():

    query = """
    CREATE TABLE IF NOT EXISTS loans (
        id SERIAL PRIMARY KEY,
        loan_name VARCHAR(100) NOT NULL,
        lender VARCHAR(100),
        principal_amount NUMERIC(15, 2) NOT NULL,
        interest_rate NUMERIC(5, 2) NOT NULL,
        tenure_months INTEGER NOT NULL,
        start_date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    execute_query(query)


# --------------------------------------------------
# Initialize
# --------------------------------------------------

try:
    initialize_database()
    database_connected = True

except Exception as error:
    database_connected = False

    st.error("Unable to connect to PostgreSQL.")
    st.exception(error)


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:

    st.title("💰 Loan Manager")

    if database_connected:
        st.success("Database Connected")
    else:
        st.error("Database Disconnected")

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Loans",
            "Payments",
            "Analytics",
        ],
    )


# --------------------------------------------------
# Dashboard
# --------------------------------------------------

if page == "Dashboard":

    st.title("💰 Loan Management Dashboard")

    st.write(
        "Manage your loans, payments, EMIs and financial analytics."
    )

    loans = read_query(
        """
        SELECT *
        FROM loans
        ORDER BY created_at DESC
        """
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total Loans",
            len(loans),
        )

    with col2:
        total_principal = (
            loans["principal_amount"].sum()
            if not loans.empty
            else 0
        )

        st.metric(
            "Total Principal",
            f"₹{total_principal:,.2f}",
        )

    with col3:
        st.metric(
            "Active Loans",
            len(loans),
        )

    st.divider()

    if loans.empty:

        st.info(
            "No loans found. Go to the Loans page to add your first loan."
        )

    else:

        st.subheader("Your Loans")

        st.dataframe(
            loans,
            width="stretch",
            hide_index=True,
        )


# --------------------------------------------------
# Loans
# --------------------------------------------------

elif page == "Loans":

    st.title("📋 Loan Management")

    tab1, tab2 = st.tabs(
        [
            "Add Loan",
            "View Loans",
        ]
    )

    # ----------------------------------------------
    # Add loan
    # ----------------------------------------------

    with tab1:

        with st.form("add_loan_form"):

            loan_name = st.text_input(
                "Loan Name",
                placeholder="e.g. Home Loan",
            )

            lender = st.text_input(
                "Lender",
                placeholder="e.g. HDFC Bank",
            )

            principal = st.number_input(
                "Principal Amount",
                min_value=0.0,
                step=1000.0,
            )

            interest_rate = st.number_input(
                "Annual Interest Rate (%)",
                min_value=0.0,
                max_value=100.0,
                step=0.1,
            )

            tenure = st.number_input(
                "Tenure (months)",
                min_value=1,
                step=1,
            )

            start_date = st.date_input(
                "Loan Start Date",
            )

            submitted = st.form_submit_button(
                "Add Loan",
                type="primary",
            )

            if submitted:

                if not loan_name:
                    st.warning("Please enter a loan name.")

                elif principal <= 0:
                    st.warning("Principal must be greater than zero.")

                else:

                    execute_query(
                        """
                        INSERT INTO loans (
                            loan_name,
                            lender,
                            principal_amount,
                            interest_rate,
                            tenure_months,
                            start_date
                        )
                        VALUES (
                            :loan_name,
                            :lender,
                            :principal,
                            :interest_rate,
                            :tenure,
                            :start_date
                        )
                        """,
                        {
                            "loan_name": loan_name,
                            "lender": lender,
                            "principal": principal,
                            "interest_rate": interest_rate,
                            "tenure": tenure,
                            "start_date": start_date,
                        },
                    )

                    st.success(
                        f"{loan_name} added successfully!"
                    )

                    st.rerun()

    # ----------------------------------------------
    # View loans
    # ----------------------------------------------

    with tab2:

        loans = read_query(
            """
            SELECT
                id,
                loan_name,
                lender,
                principal_amount,
                interest_rate,
                tenure_months,
                start_date
            FROM loans
            ORDER BY created_at DESC
            """
        )

        if loans.empty:

            st.info("No loans available.")

        else:

            st.dataframe(
                loans,
                width="stretch",
                hide_index=True,
            )


# --------------------------------------------------
# Payments
# --------------------------------------------------

elif page == "Payments":

    st.title("💳 Payments")

    st.info(
        "Payment tracking will be added next."
    )


# --------------------------------------------------
# Analytics
# --------------------------------------------------

elif page == "Analytics":

    st.title("📊 Analytics")

    st.info(
        "Loan analytics and visualizations will be added next."
    )
