# python
import psycopg2

conn = psycopg2.connect(
    host="127.0.0.1",
    database="inventory",
    user="admin",
    password="admin",
    port=5432,
)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS sanity_check(id serial PRIMARY KEY, note text);")
cur.execute("INSERT INTO sanity_check(note) VALUES (%s) RETURNING id;", ("hello db",))
row_id = cur.fetchone()[0]
conn.commit()

cur.execute("SELECT id, note FROM sanity_check WHERE id = %s;", (row_id,))
print("Row:", cur.fetchone())

cur.close()
conn.close()
print("OK")