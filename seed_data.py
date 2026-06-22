import psycopg2
import random
from faker import Faker
from datetime import date, timedelta

# Initialize Faker (using UK locale for realistic names/plates)
fake = Faker('en_GB')

# Standard UK fleet vehicles to bypass the Faker error
TAXI_MODELS = ['Toyota Prius', 'Skoda Octavia', 'Kia Niro', 'Hyundai Ioniq', 'Nissan Leaf', 'MG5 EV', 'VW Passat', 'Ford Mondeo']

def generate_mock_data():
    try:
        # BULLETPROOF CONNECTION: Bypasses all URL formatting issues
        conn = psycopg2.connect(
            host="db.dozshatclimtifgtxajt.supabase.co",
            port="5432",
            database="postgres",
            user="postgres",
            password="A0304Shirw@"
        )
        
        cursor = conn.cursor()
        print("Connected to Supabase. Seeding compliant data...")

        # 1. Insert 20 Drivers
        driver_ids = []
        for _ in range(20):
            cursor.execute(
                """
                INSERT INTO Drivers (Name, Phone, Email, Status)
                VALUES (%s, %s, %s, %s) RETURNING Driver_ID;
                """,
                (fake.name(), fake.phone_number(), fake.email(), 'Active')
            )
            driver_ids.append(cursor.fetchone()[0])

        # 2. Insert 15 Vehicles
        vehicle_ids = []
        for _ in range(15):
            cursor.execute(
                """
                INSERT INTO Vehicles (License_Plate, Make_Model, Lease_Expiry_Date)
                VALUES (%s, %s, %s) RETURNING Vehicle_ID;
                """,
                # Randomly pick from our list instead of relying on Faker
                (fake.license_plate(), random.choice(TAXI_MODELS), fake.date_between(start_date='today', end_date='+2y'))
            )
            vehicle_ids.append(cursor.fetchone()[0])

        # Setup Dates for Alert Testing
        today = date.today()
        test_dates = [
            today + timedelta(days=10), # Triggers 10-day alert
            today + timedelta(days=14), # Triggers 14-day alert
            today - timedelta(days=5),  # Overdue
            today + timedelta(days=100) # Safe
        ]

        # 3. Insert Driver Documents
        driver_docs = ['DVLA Licence', 'BCC Driver Badge', 'Enhanced DBS', 'Medical Certificate']
        for d_id in driver_ids:
            for doc in driver_docs:
                expiry = random.choice(test_dates) if random.random() > 0.6 else fake.date_between(start_date='today', end_date='+1y')
                fake_url = f"https://fake-s3-bucket.com/{d_id}_{doc.replace(' ', '_')}.pdf"
                
                cursor.execute(
                    """
                    INSERT INTO Documents (Driver_ID, Vehicle_ID, Doc_Type, File_URL, Expiry_Date, Status)
                    VALUES (%s, NULL, %s, %s, %s, %s);
                    """,
                    (d_id, doc, fake_url, expiry, 'Active')
                )

        # 4. Insert Vehicle Documents
        vehicle_docs = ['BCC Vehicle Licence', 'Hire & Reward Insurance', 'VST Certificate']
        for v_id in vehicle_ids:
            # Expiring vehicle documents
            for doc in vehicle_docs:
                expiry = random.choice(test_dates) if random.random() > 0.6 else fake.date_between(start_date='today', end_date='+1y')
                fake_url = f"https://fake-s3-bucket.com/veh_{v_id}_{doc.replace(' ', '_')}.pdf"
                
                cursor.execute(
                    """
                    INSERT INTO Documents (Driver_ID, Vehicle_ID, Doc_Type, File_URL, Expiry_Date, Status)
                    VALUES (NULL, %s, %s, %s, %s, %s);
                    """,
                    (v_id, doc, fake_url, expiry, 'Active')
                )
            
            # The V5C Logbook edge case (NO expiry date)
            fake_v5c_url = f"https://fake-s3-bucket.com/veh_{v_id}_V5C_Logbook.pdf"
            cursor.execute(
                """
                INSERT INTO Documents (Driver_ID, Vehicle_ID, Doc_Type, File_URL, Expiry_Date, Status)
                VALUES (NULL, %s, %s, %s, NULL, %s);
                """,
                (v_id, 'V5C Logbook', fake_v5c_url, 'Active')
            )

        conn.commit()
        cursor.close()
        conn.close()
        print("Success! Database populated with compliant driver and vehicle data.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    generate_mock_data()