import sqlite3
conn = sqlite3.connect('blog.db')
conn.execute("UPDATE users SET role = 'ADMIN' WHERE username = 'testadmin'")
conn.commit()
print("Done!")
print(conn.execute("SELECT id, username, role FROM users").fetchall())