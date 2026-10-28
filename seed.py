"""Optional: fill the database with demo data.  Run:  python seed.py
Demo login -> email: demo@student.com   password: demo1234"""
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
import app as a

with a.app.app_context():
    if a.query("SELECT id FROM users WHERE email='demo@student.com'", one=True):
        print("Demo data already exists."); raise SystemExit
    uid = a.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                    ("Demo Student", "demo@student.com", generate_password_hash("demo1234")))
    a.execute("""INSERT INTO brands(user_id,brand_name,slug,bio,niche,instagram,linkedin)
        VALUES(?,?,?,?,?,?,?)""", (uid, "Crafty Campus", "crafty-campus",
        "Handmade accessories by a BCA student.", "handmade accessories",
        "https://instagram.com/", "https://linkedin.com/"))
    today = date.today()
    pids = [a.execute("INSERT INTO products(user_id,name,price,description) VALUES(?,?,?,?)",
            (uid, n, p, d)) for n, p, d in [
            ("Beaded Bracelet", 149, "Colourful handmade bracelet"),
            ("Tote Bag", 299, "Hand-painted canvas bag")]]
    posts = [a.execute("INSERT INTO posts(user_id,platform,caption,hashtags,scheduled_date,status) VALUES(?,?,?,?,?,?)",
            (uid, pl, cap, "#handmade #student", (today + timedelta(days=d)).isoformat(), st))
            for pl, cap, d, st in [("Instagram", "New bracelets are here!", -5, "posted"),
                                   ("LinkedIn", "My journey as a student founder", -2, "posted"),
                                   ("Instagram", "Tote bag giveaway this weekend", 2, "scheduled")]]
    for i in range(6):
        d = (today - timedelta(days=30 - i * 5)).isoformat()
        a.execute("INSERT INTO metrics(user_id,platform,record_date,followers,likes,clicks) VALUES(?,?,?,?,?,?)",
                  (uid, "Instagram", d, 120 + i * 35, 40 + i * 10, 5 + i * 3))
        a.execute("INSERT INTO metrics(user_id,platform,record_date,followers,likes,clicks) VALUES(?,?,?,?,?,?)",
                  (uid, "LinkedIn", d, 50 + i * 12, 15 + i * 4, 2 + i))
    for pid, post, q, off in [(pids[0], posts[0], 3, 4), (pids[1], posts[0], 1, 3), (pids[0], posts[1], 2, 1)]:
        a.execute("INSERT INTO orders(user_id,product_id,post_id,quantity,order_date) VALUES(?,?,?,?,?)",
                  (uid, pid, post, q, (today - timedelta(days=off)).isoformat()))
    print("Demo data added. Login: demo@student.com / demo1234")
