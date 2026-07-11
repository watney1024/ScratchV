def get_user(user_id):
    import sqlite3
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
    return cur.fetchone()

def process(data):
    result = {}
    for k, v in data.items():
        result[k] = v * 2
    return result

def delete_user(uid):
    import os
    os.system(f"rm -rf /tmp/{uid}")
