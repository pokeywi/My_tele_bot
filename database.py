import sqlite3

def create_db():
    conn = sqlite3.connect("movies.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            file_id TEXT NOT NULL,
            quality TEXT,
            size INTEGER
        )
    """)
    conn.commit()
    conn.close()

def insert_video(title, file_id, quality=None, size=0):
    conn = sqlite3.connect("movies.db")
    c = conn.cursor()
    c.execute("INSERT INTO videos (title, file_id, quality, size) VALUES (?, ?, ?, ?)", (title, file_id, quality, size))
    conn.commit()
    conn.close()

def search_videos(query):
    conn = sqlite3.connect("movies.db")
    c = conn.cursor()
    c.execute("SELECT id, title, file_id, quality, size FROM videos WHERE LOWER(title) LIKE ?", ('%' + query.lower() + '%',))
    results = c.fetchall()
    conn.close()
    return results

def get_video_by_id(video_id):
    conn = sqlite3.connect("movies.db")
    c = conn.cursor()
    c.execute("SELECT title, file_id FROM videos WHERE id = ?", (video_id,))
    result = c.fetchone()
    conn.close()
    return result