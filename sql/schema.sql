DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS guests;
DROP TABLE IF EXISTS hotels;


CREATE TABLE rooms (
    room_type_id INT PRIMARY KEY,
    room_type_name TEXT NOT NULL,
    base_rate FLOAT NOT NULL
);

CREATE TABLE guests (
    guest_id INT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL,
    loyalty_member INT NOT NULL
);

CREATE TABLE hotels (
    hotel_id INT PRIMARY KEY,
    hotel_name TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE bookings (
    booking_id INT PRIMARY KEY,
    guest_id INT NOT NULL REFERENCES guests(guest_id),
    hotel_id INT NOT NULL REFERENCES hotels(hotel_id),
    room_type_id INT NOT NULL REFERENCES rooms(room_type_id),
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    nights INT NOT NULL,
    rate_per_night DECIMAL(10, 2) NOT NULL,
    total_revenue DECIMAL(10, 2) NOT NULL,
    satisfaction_score INT,
    booking_channel TEXT NOT NULL,
    data_quality_flag TEXT NOT NULL DEFAULT 'OK'
);