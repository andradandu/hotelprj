import os
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = "data"
SCHEMA_PATH = "sql/schema.sql"
EXPORT_DIR = "output"
REJECTED_PATH = "output/rejected_rows.csv"

# 1. Connect to database
os.makedirs(EXPORT_DIR, exist_ok=True)
engine = create_engine(f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('HOST', 'localhost')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}")




# 2. Load data for bronze tables
def load_bronze_table(table_name):
    file_path = os.path.join(RAW_DIR, f"{table_name}_raw.csv")
    df = pd.read_csv(file_path, dtype=str)
    bronze_table = f"bronze_{table_name}"
    df.to_sql(bronze_table, engine, if_exists='replace', index=False)
    print(f"Loaded {len(df)} rows into {bronze_table} table.")
    return df

bookings_df_raw = load_bronze_table("bookings")
guests_df_raw = load_bronze_table("guests")
hotels_df_raw = load_bronze_table("hotels")
room_types_df_raw  = load_bronze_table("rooms")




# 3. BRONZE TO SILVER: Deduplicate and clean data

#GUESTS
guests_df = guests_df_raw.copy()
guests_df['guest_id'] = guests_df['guest_id'].astype(int)
guests_df = guests_df.drop_duplicates()
guests_df['first_name'] = guests_df['first_name'].str.strip().str.title()  # Normalize first names
guests_df['last_name'] = guests_df['last_name'].str.strip().str.title()  # Normalize last names
guests_df['email'] = guests_df['email'].str.strip().str.lower()  # Normalize emails
guests_df['country'] = guests_df['country'].str.strip().str.upper()  # Normalize country codes
dict_loyaly = {'True': 1, 'False': 0}
guests_df['loyalty_member'] = guests_df['loyalty_member'].map(dict_loyaly)  # Convert loyalty_member to INT 1: true, 0: false
guests_df.to_sql("silver_guests", engine, if_exists='replace', index=False)


#HOTELS
hotels_df = hotels_df_raw.copy()
hotels_df['hotel_id'] = hotels_df['hotel_id'].astype(int)
hotels_df = hotels_df.drop_duplicates(subset=['hotel_id'])  # Deduplicate based on hotel_id
hotels_df['hotel_name'] = hotels_df['hotel_name'].str.strip().str.title()  # Normalize hotel names
hotels_df.to_sql("silver_hotels", engine, if_exists='replace', index=False)

#ROOM TYPES
room_types_df = room_types_df_raw.copy()
room_types_df['room_type_id'] = room_types_df['room_type_id'].astype(int)
room_types_df = room_types_df.drop_duplicates()
room_types_df['room_type_name'] = room_types_df['room_type_name'].str.strip().str.title()  # Normalize room type names
room_types_name_map = room_types_df.set_index('room_type_id')['room_type_name'].to_dict() # map of room_type_id to normalized
room_types_df['base_rate'] = room_types_df['base_rate'].fillna(0).astype(float)
room_types_df.to_sql("silver_rooms", engine, if_exists='replace', index=False)

#BOOKINGS
bookings_df = bookings_df_raw.copy()
bookings_df['booking_id'] = bookings_df['booking_id'].astype(int)
bookings_df = bookings_df.drop_duplicates(subset=['booking_id'])  # Deduplicate based on booking_id

bookings_df['check_in'] = pd.to_datetime(bookings_df['check_in'], errors='coerce')  # Convert to datetime, coerce errors to NaT
bookings_df['check_out'] = pd.to_datetime(bookings_df['check_out'], errors='coerce')  # Convert to datetime, coerce errors to NaT
bookings_df.dropna(subset=['check_in', 'check_out'], inplace=True)  # Drop rows with invalid dates
bookings_df.drop(bookings_df[bookings_df['check_out'] <= bookings_df['check_in']].index, inplace=True)  # Drop rows where check_out is not after check_in

bookings_df['nights'] = pd.to_numeric(bookings_df['nights']).astype('Int64')  # Convert to nullable integer
false_nights = bookings_df['nights'] <= 0
bookings_df['data_quality_flag'] = 'OK'
if false_nights.any():
    bookings_df.loc[false_nights, 'data_quality_flag'] = 'Invalid nights'
    bookings_df[false_nights].to_csv(REJECTED_PATH, index=False)  # Export rejected rows for review
    

bookings_df['rate_per_night'] = bookings_df['rate_per_night'].astype(float)
bookings_df['total_revenue'] = bookings_df['total_revenue'].astype(float)
expected_revenue = bookings_df['nights'] * bookings_df['rate_per_night']
revenue_mismatch = (bookings_df['total_revenue'] - expected_revenue).abs() > 0.01  # Allow small rounding errors
if revenue_mismatch.any():
    bookings_df.loc[revenue_mismatch, 'data_quality_flag'] = 'Revenue mismatch'
    bookings_df[revenue_mismatch].to_csv(REJECTED_PATH, mode='a', header=False, index=False)

name_to_id = {r["hotel_name"]: r["hotel_id"] for _, r in hotels_df.iterrows()}
bookings_df["hotel_id"] = bookings_df["hotel_name_raw"].map(name_to_id)

bookings_df.dropna(subset=['hotel_id'], inplace=True)  # Drop rows where hotel_id could not be mapped
bookings_df['satisfaction_score'] = pd.to_numeric(bookings_df['satisfaction_score'], errors='coerce').astype('Int64')  # Convert to nullable integer

bookings_df.to_sql("silver_bookings", engine, if_exists='replace', index=False)







# 4. SILVER TO GOLD: CREATE STAR SCHEMA TABLES
raw_conn = psycopg2.connect(host=os.getenv('HOST', 'localhost'),
                            port=os.getenv('POSTGRES_PORT'),
                            dbname=os.getenv('POSTGRES_DB'),
                            user=os.getenv('POSTGRES_USER'),
                            password=os.getenv('POSTGRES_PASSWORD'))

raw_conn.autocommit = True
with raw_conn.cursor() as cur:
    with open(SCHEMA_PATH) as f:
        cur.execute(f.read())
raw_conn.close()

hotels=hotels_df[["hotel_id", "hotel_name", "city", "country"]]
hotels.to_sql("hotels", engine, if_exists="append", index=False)

room_types=room_types_df[["room_type_id", "room_type_name", "base_rate"]]
room_types.to_sql("rooms", engine, if_exists="append", index=False)

guests=guests_df[["guest_id", "first_name", "last_name", "email", "country", "loyalty_member"]]
guests.to_sql("guests", engine, if_exists="append", index=False)

bookings=bookings_df[["booking_id", "guest_id", "hotel_id", "room_type_id", "check_in", "check_out", "nights", "rate_per_night", "total_revenue", "satisfaction_score", "booking_channel", "data_quality_flag"]]
bookings.to_sql("bookings", engine, if_exists="append", index=False)



# Export cleaned data to CSV for downstream consumption
bookings.to_csv(os.path.join(EXPORT_DIR, "bookings_gold.csv"), index=False)
guests.to_csv(os.path.join(EXPORT_DIR, "guests_gold.csv"), index=False)
hotels.to_csv(os.path.join(EXPORT_DIR, "hotels_gold.csv"), index=False)
room_types.to_csv(os.path.join(EXPORT_DIR, "room_types_gold.csv"), index=False)  

