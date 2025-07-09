import sqlite3

def get_db_connection():
    conn = sqlite3.connect("college_users.db")
    conn.row_factory = sqlite3.Row  # بترجع النتائج كـ dict
    return conn
