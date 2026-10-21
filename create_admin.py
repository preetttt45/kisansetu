
from database.database import get_db_connection
from werkzeug.security import generate_password_hash
from getpass import getpass


def create_admin():
    print("\n--- Create KisanSetu AI Admin ---")

    name = input("Enter admin name: ").strip()
    email = input("Enter admin email: ").strip().lower()
    password = getpass("Enter a new admin password: ")

    if not name or not email or not password:
        print("Error: All fields are required.")
        return

    if len(password) < 8:
        print("Error: Password must be at least 8 characters.")
        return

    connection = get_db_connection()

    try:
        existing_user = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            print("Error: This email is already registered.")
            return

        connection.execute(
            """
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, 'admin')
            """,
            (name, email, generate_password_hash(password))
        )

        connection.commit()
        print("\nAdmin account created successfully!")

    except Exception as error:
        connection.rollback()
        print("Could not create admin:", error)

    finally:
        connection.close()


if __name__ == "__main__":
    create_admin()
