import psycopg2
import smtplib
from email.message import EmailMessage
from datetime import date, timedelta

# --- CONFIGURATION ---
# Set to False to actually send emails. Set to True to just print them to the terminal for testing.
DRY_RUN = True 

# Email Credentials (e.g., your prototype Gmail account)
# NOTE: If using Gmail, you MUST use an "App Password", not your normal login password.
EMAIL_SENDER = "your-prototype-email@gmail.com"
EMAIL_PASSWORD = "your-app-password-here"

# --- DATABASE CONNECTION ---
def get_db_connection():
    # Reverting to the direct connection (Port 5432) now that the IP ban has lifted.
    # This completely bypasses the pooler's SASL bugs with special characters.
    return psycopg2.connect(
        host="db.dozshatclimtifgtxajt.supabase.co",
        port="5432",
        database="postgres",
        user="postgres",
        password="A0304Shirw@"
    )

def send_email(driver_name, driver_email, doc_type, expiry_date):
    """Constructs and sends the email warning."""
    days_left = (expiry_date - date.today()).days
    
    subject = f"URGENT: Your {doc_type} expires in {days_left} days"
    body = f"""Hi {driver_name},

This is an automated alert from the Fleet Management System. 

Your {doc_type} is due to expire on {expiry_date.strftime('%d %b %Y')}. 
You have exactly {days_left} days remaining.

Please ensure you provide an updated copy to the office immediately to avoid suspension.

Thank you,
Fleet Management Team
"""

    if DRY_RUN:
        print("--------------------------------------------------")
        print(f"[DRY RUN] Would send to: {driver_email}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        print("--------------------------------------------------")
        return

    # Actual email sending logic
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_SENDER
        msg['To'] = driver_email

        # Connect to Gmail's SMTP server
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email successfully sent to {driver_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {driver_email}. Error: {e}")

def run_alerts():
    print("Starting daily compliance check...")
    
    # Calculate target window (next 14 days)
    today = date.today()
    target_14_days = today + timedelta(days=14)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query for documents expiring anywhere within the next 14 days
        # This guarantees we catch the mock data regardless of how many days have passed
        query = """
        SELECT 
            d.Name, 
            d.Email,
            doc.Doc_Type, 
            doc.Expiry_Date
        FROM Documents doc
        JOIN Drivers d ON doc.Driver_ID = d.Driver_ID
        WHERE doc.Status = 'Active'
        AND doc.Expiry_Date > CURRENT_DATE
        AND doc.Expiry_Date <= %s;
        """
        
        cursor.execute(query, (target_14_days,))
        alerts = cursor.fetchall()
        
        if not alerts:
            print("No documents expiring in the next 14 days. No emails to send.")
        else:
            print(f"Found {len(alerts)} alerts to trigger today.")
            for alert in alerts:
                driver_name, driver_email, doc_type, expiry_date = alert
                send_email(driver_name, driver_email, doc_type, expiry_date)
                
        cursor.close()
        conn.close()
        
    except psycopg2.OperationalError as e:
        print("\n❌ DATABASE CONNECTION BLOCKED")
        print("Error Details:", e)
        print("-> If you still see a timeout, the 30-minute Fail2Ban block is still ticking down.")
        print("-> Make sure Streamlit is stopped (Ctrl+C in its terminal) so it doesn't take the connection first!")
    except Exception as e:
        print(f"Database error occurred: {e}")

if __name__ == "__main__":
    run_alerts()