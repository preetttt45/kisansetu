import sqlite3

DATABASE = "database/kesansetu.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    connection.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER NOT NULL,
        crop_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        quality TEXT NOT NULL,
        location TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (farmer_id) REFERENCES users(id)
    )
""")


    
    connection.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        total_price REAL NOT NULL,
        status TEXT DEFAULT 'Pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (buyer_id) REFERENCES users(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
""")


   
    connection.execute("""
        CREATE TABLE IF NOT EXISTS logistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL UNIQUE,
            delivery_method TEXT NOT NULL
                CHECK (delivery_method IN ('Delivery', 'Self Pickup')),
            delivery_address TEXT,
            transport_name TEXT,
            vehicle_number TEXT,
            driver_contact TEXT,
            delivery_status TEXT NOT NULL DEFAULT 'Pending Assignment',
            assigned_at TIMESTAMP,
            delivered_at TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
 


    connection.commit()
    connection.close()