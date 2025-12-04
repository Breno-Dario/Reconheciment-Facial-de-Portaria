import psycopg2

def get_connection():
    return psycopg2.connect(
        host="localhost",       
        database="face_db",
        user="admin",
        password="admin",
        port=5433
    )
