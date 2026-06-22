import streamlit as st
import pandas as pd
import psycopg2
from datetime import date

# --- PAGE SETUP ---
st.set_page_config(page_title="Taxi Fleet Compliance", page_icon="🚖", layout="wide")
st.title("🚖 Taxi Fleet Compliance Dashboard")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Professional UI tweaks for a clean, modern dashboard */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e6ed;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f8f9fa;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e2e8f0;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
# Using the bulletproof connection method with key-value pairs to handle special characters
def get_db_connection():
    return psycopg2.connect(
        host="db.dozshatclimtifgtxajt.supabase.co",
        port="5432",
        database="postgres",
        user="postgres",
        password="A0304Shirw@"
    )

# --- DATA FETCHING ---
# Streamlit caches this so it doesn't hit the database every single time you click a button
@st.cache_data(ttl=60)
def load_compliance_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Bring Drivers, Vehicles, and Documents into one unified view
    query = """
    SELECT 
        COALESCE(d.Name, 'N/A') AS "Driver Name",
        COALESCE(v.License_Plate, 'N/A') AS "Vehicle Plate",
        doc.Doc_Type AS "Document Type",
        doc.Expiry_Date AS "Expiry Date",
        doc.Status
    FROM Documents doc
    LEFT JOIN Drivers d ON doc.Driver_ID = d.Driver_ID
    LEFT JOIN Vehicles v ON doc.Vehicle_ID = v.Vehicle_ID
    WHERE doc.Status = 'Active'
    ORDER BY doc.Expiry_Date ASC;
    """
    
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    data = cursor.fetchall()
    
    conn.close()
    return pd.DataFrame(data, columns=columns)

# --- VISUAL ALERTING LOGIC ---
def highlight_expiring_rows(row):
    # If there is no expiry date (like the V5C Logbook), leave it blank
    if pd.isnull(row['Expiry Date']):
        return [''] * len(row)
    
    # Safely convert to a pandas datetime object before doing math
    expiry = pd.to_datetime(row['Expiry Date'])
    days_until = (expiry - pd.Timestamp.today().normalize()).days
    
    if days_until < 0:
        # Red background for expired documents
        return ['background-color: rgba(255, 0, 0, 0.2)'] * len(row)
    elif days_until <= 30:
        # Yellow background for documents expiring in the next 30 days
        return ['background-color: rgba(255, 204, 0, 0.3)'] * len(row)
    
    return [''] * len(row)

df = load_compliance_data()

# --- KPI METRICS ---
# Calculate days until expiry for metrics (ignore V5C logbooks with no expiry)
df_metrics = df.copy()

# Fix: Keep everything in Pandas native datetime format to calculate the days difference
today = pd.Timestamp.today().normalize()
df_metrics['Days Until'] = (pd.to_datetime(df_metrics['Expiry Date'], errors='coerce') - today).dt.days

expired_count = len(df_metrics[df_metrics['Days Until'] < 0])
warning_count = len(df_metrics[(df_metrics['Days Until'] >= 0) & (df_metrics['Days Until'] <= 30)])
safe_count = len(df) - expired_count - warning_count

# Render KPI Row
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("🚨 Overdue Documents", expired_count, delta="Action Required", delta_color="inverse")
with col2:
    st.metric("⚠️ Expiring < 30 Days", warning_count, delta="Upcoming Renewals", delta_color="off")
with col3:
    st.metric("✅ Compliant Documents", safe_count, delta="Good Standing", delta_color="normal")

st.divider()

# --- MAIN INTERFACE (TABS) ---
tab1, tab2 = st.tabs(["📋 Compliance Report", "👥 Manage Drivers"])

with tab1:
    st.subheader("Current Fleet Compliance")
    st.write("Documents highlighted in **Yellow** expire within 30 days. Documents in **Red** are overdue.")
    
    # Interactive Filters
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        driver_list = df['Driver Name'].unique().tolist()
        if 'N/A' in driver_list: driver_list.remove('N/A')
        driver_filter = st.multiselect("Filter by Driver Name", options=sorted(driver_list))
    with filter_col2:
        status_filter = st.radio("Filter Status", ["All", "Action Required", "Compliant"], horizontal=True)

    # Apply Filters
    display_df = df_metrics.copy()
    if driver_filter:
        display_df = display_df[display_df['Driver Name'].isin(driver_filter)]
        
    if status_filter == "Action Required":
        display_df = display_df[display_df['Days Until'] <= 30]
    elif status_filter == "Compliant":
        display_df = display_df[(display_df['Days Until'] > 30) | (display_df['Days Until'].isna())]

    # Clean up the dataframe before rendering
    display_df = display_df.drop(columns=['Days Until'])

    # Render the interactive table
    st.dataframe(
        display_df.style.apply(highlight_expiring_rows, axis=1), 
        width='stretch', 
        hide_index=True
    )

with tab2:
    st.subheader("Add New Driver")
    
    # Professional container formatting
    with st.container(border=True):
        st.markdown("Enter the driver's details below to register them in the system.")
        
        with st.form("add_driver_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Full Name *", placeholder="e.g. Jane Doe")
                new_phone = st.text_input("Phone Number", placeholder="e.g. 07700 900000")
            with col2:
                new_email = st.text_input("Email Address *", placeholder="e.g. jane@example.com")
                
            st.markdown("<br>", unsafe_allow_html=True)
            submit_button = st.form_submit_button("Register Driver", type="primary", width='stretch')
            
            if submit_button:
                if new_name and new_email:
                    with st.spinner("Registering driver securely..."):
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO Drivers (Name, Phone, Email, Status) VALUES (%s, %s, %s, 'Active')",
                            (new_name, new_phone, new_email)
                        )
                        conn.commit()
                        conn.close()
                        
                    st.success(f"✅ Driver '{new_name}' has been successfully added to the database.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("⚠️ Name and Email are legally required fields.")