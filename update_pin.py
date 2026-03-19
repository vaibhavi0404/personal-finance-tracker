import sqlite3

conn = sqlite3.connect('users.db')
cur = conn.cursor()

# Set default PIN 1234 for users where pin is NULL or empty
cur.execute("UPDATE users SET pin='1234' WHERE pin IS NULL OR pin=''")

conn.commit()
conn.close()

print("PINs updated for existing users.")