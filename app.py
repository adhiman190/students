"""StudentBrand Hub - Flask backend."""
import os
import re
import random
import sqlite3
from datetime import date
from functools import wraps

from flask import (Flask, g, render_template, request, redirect,
                   url_for, session, flash, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-this-key")
app.config["DATABASE"] = os.path.join(BASE, "database.db")
app.config["UPLOAD_FOLDER"] = os.path.join(BASE, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB uploads
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
PLATFORMS = ["Instagram", "LinkedIn", "YouTube"]


# ---------- database helpers ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(app.config["DATABASE"])
    with open(os.path.join(BASE, "schema.sql")) as f:
        db.executescript(f.read())
    db.commit()
    db.close()


def query(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


# ---------- auth ----------
@app.before_request
def load_user():
    g.user = g.brand = None
    uid = session.get("user_id")
    if uid:
        g.user = query("SELECT * FROM users WHERE id=?", (uid,), one=True)
        if g.user is None:
            session.clear()
        else:
            g.brand = query("SELECT * FROM brands WHERE user_id=?", (uid,), one=True)


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if g.user is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*a, **kw)
    return wrapped


@app.route("/")
def index():
    if g.user:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Fill all fields. Password must be at least 6 characters.", "error")
        elif query("SELECT id FROM users WHERE email=?", (email,), one=True):
            flash("This email is already registered.", "error")
        else:
            uid = execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                          (name, email, generate_password_hash(password)))
            session.clear()
            session["user_id"] = uid
            flash("Account created! Set up your brand profile.", "success")
            return redirect(url_for("profile"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query("SELECT * FROM users WHERE email=?", (email,), one=True)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Wrong email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------- dashboard ----------
@app.route("/dashboard")
@login_required
def dashboard():
    uid = g.user["id"]
    today = date.today().isoformat()
    stats = {
        "posts": query("SELECT COUNT(*) c FROM posts WHERE user_id=?", (uid,), one=True)["c"],
        "scheduled": query("SELECT COUNT(*) c FROM posts WHERE user_id=? AND status='scheduled'", (uid,), one=True)["c"],
        "followers": query("""SELECT COALESCE(SUM(followers),0) c FROM metrics m
            WHERE user_id=? AND record_date=(SELECT MAX(record_date) FROM metrics
            WHERE user_id=m.user_id AND platform=m.platform)""", (uid,), one=True)["c"],
        "orders": query("SELECT COALESCE(SUM(quantity),0) c FROM orders WHERE user_id=?", (uid,), one=True)["c"],
        "revenue": query("""SELECT COALESCE(SUM(p.price*o.quantity),0) c FROM orders o
            JOIN products p ON p.id=o.product_id WHERE o.user_id=?""", (uid,), one=True)["c"],
    }
    upcoming = query("""SELECT * FROM posts WHERE user_id=? AND status='scheduled'
        AND scheduled_date>=? ORDER BY scheduled_date LIMIT 5""", (uid, today))
    return render_template("dashboard.html", stats=stats, upcoming=upcoming)


# ---------- brand profile ----------
def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "brand"


def unique_slug(text, own_id=None):
    base = slugify(text)
    slug, n = base, 1
    while True:
        row = query("SELECT user_id FROM brands WHERE slug=?", (slug,), one=True)
        if row is None or row["user_id"] == own_id:
            return slug
        n += 1
        slug = f"{base}-{n}"


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        f = request.form
        brand_name = f.get("brand_name", "").strip()
        if not brand_name:
            flash("Brand name is required.", "error")
            return redirect(url_for("profile"))
        logo = g.brand["logo"] if g.brand else None
        file = request.files.get("logo")
        if file and file.filename:
            ext = file.filename.rsplit(".", 1)[-1].lower()
            if ext in ALLOWED_EXT:
                logo = f"{g.user['id']}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], logo))
            else:
                flash("Logo must be png, jpg, gif or webp.", "error")
                return redirect(url_for("profile"))
        vals = (brand_name, f.get("bio", "").strip(), f.get("niche", "").strip(), logo,
                f.get("instagram", "").strip(), f.get("linkedin", "").strip(),
                f.get("youtube", "").strip(), f.get("website", "").strip())
        if g.brand:
            slug = unique_slug(brand_name, g.user["id"])
            execute("""UPDATE brands SET brand_name=?,bio=?,niche=?,logo=?,instagram=?,
                linkedin=?,youtube=?,website=?,slug=? WHERE user_id=?""",
                    vals + (slug, g.user["id"]))
        else:
            execute("""INSERT INTO brands(brand_name,bio,niche,logo,instagram,linkedin,
                youtube,website,slug,user_id) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    vals + (unique_slug(brand_name), g.user["id"]))
        flash("Brand profile saved.", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html")


# ---------- post planner ----------
@app.route("/planner", methods=["GET", "POST"])
@login_required
def planner():
    uid = g.user["id"]
    if request.method == "POST":
        platform = request.form.get("platform")
        caption = request.form.get("caption", "").strip()
        hashtags = request.form.get("hashtags", "").strip()
        when = request.form.get("scheduled_date", "")
        if platform not in PLATFORMS or not caption or not when:
            flash("Platform, caption and date are required.", "error")
        else:
            execute("""INSERT INTO posts(user_id,platform,caption,hashtags,scheduled_date)
                VALUES(?,?,?,?,?)""", (uid, platform, caption, hashtags, when))
            flash("Post added to your planner.", "success")
        return redirect(url_for("planner"))
    flt = request.args.get("platform")
    if flt in PLATFORMS:
        posts = query("SELECT * FROM posts WHERE user_id=? AND platform=? ORDER BY scheduled_date DESC", (uid, flt))
    else:
        posts = query("SELECT * FROM posts WHERE user_id=? ORDER BY scheduled_date DESC", (uid,))
    return render_template("planner.html", posts=posts, platforms=PLATFORMS,
                           flt=flt, today=date.today().isoformat())


@app.route("/posts/<int:pid>/toggle", methods=["POST"])
@login_required
def toggle_post(pid):
    post = query("SELECT * FROM posts WHERE id=? AND user_id=?", (pid, g.user["id"]), one=True)
    if post is None:
        abort(404)
    new = "posted" if post["status"] == "scheduled" else "scheduled"
    execute("UPDATE posts SET status=? WHERE id=?", (new, pid))
    return redirect(request.referrer or url_for("planner"))


@app.route("/posts/<int:pid>/delete", methods=["POST"])
@login_required
def delete_post(pid):
    execute("UPDATE orders SET post_id=NULL WHERE post_id=? AND user_id=?", (pid, g.user["id"]))
    execute("DELETE FROM posts WHERE id=? AND user_id=?", (pid, g.user["id"]))
    flash("Post deleted.", "success")
    return redirect(url_for("planner"))


# ---------- caption & hashtag generator (rule-based) ----------
CAPTION_TEMPLATES = {
    "friendly": [
        "Hey everyone! Meet {product} from {brand}. Made by a student, made with love. Check it out!",
        "New drop alert! {product} is now live at {brand}. Tell us what you think in the comments!",
        "Studying by day, building {brand} by night. Here is our latest: {product}.",
    ],
    "professional": [
        "Introducing {product} by {brand}. Designed to deliver real value in {niche}.",
        "{brand} is proud to present {product}. Learn more through the link in our bio.",
        "Quality, consistency and innovation in {niche}: this is {product} from {brand}.",
    ],
    "promo": [
        "LIMITED OFFER! Get {product} from {brand} at a special student price. Order today!",
        "Don't miss out: {product} is available now. DM {brand} to place your order!",
        "Big news: {product} is here. First 10 buyers get a surprise gift from {brand}!",
    ],
}
BASE_TAGS = {
    "Instagram": ["instagood", "studententrepreneur", "smallbusiness", "supportlocal"],
    "LinkedIn": ["entrepreneurship", "studentlife", "branding", "growth"],
    "YouTube": ["youtubeshorts", "studentbusiness", "startup", "subscribe"],
}


@app.route("/generator", methods=["GET", "POST"])
@login_required
def generator():
    result = None
    if request.method == "POST":
        product = request.form.get("product", "").strip() or "our new product"
        niche = request.form.get("niche", "").strip() or (g.brand["niche"] if g.brand and g.brand["niche"] else "our field")
        tone = request.form.get("tone", "friendly")
        platform = request.form.get("platform", "Instagram")
        brand = g.brand["brand_name"] if g.brand else "our brand"
        template = random.choice(CAPTION_TEMPLATES.get(tone, CAPTION_TEMPLATES["friendly"]))
        caption = template.format(product=product, brand=brand, niche=niche)
        words = [w for w in re.findall(r"[a-z0-9]+", f"{niche} {product}".lower()) if len(w) > 2]
        tags = list(dict.fromkeys(words + [slugify(brand).replace("-", "")] + BASE_TAGS.get(platform, [])))
        result = {"caption": caption, "hashtags": " ".join("#" + t for t in tags[:10]),
                  "platform": platform}
    return render_template("generator.html", result=result, platforms=PLATFORMS)


# ---------- analytics ----------
@app.route("/analytics", methods=["GET", "POST"])
@login_required
def analytics():
    uid = g.user["id"]
    if request.method == "POST":
        try:
            platform = request.form["platform"]
            rec = request.form["record_date"]
            followers = max(0, int(request.form.get("followers") or 0))
            likes = max(0, int(request.form.get("likes") or 0))
            clicks = max(0, int(request.form.get("clicks") or 0))
            if platform not in PLATFORMS or not rec:
                raise ValueError
            execute("""INSERT INTO metrics(user_id,platform,record_date,followers,likes,clicks)
                VALUES(?,?,?,?,?,?)""", (uid, platform, rec, followers, likes, clicks))
            flash("Analytics entry saved.", "success")
        except (ValueError, KeyError):
            flash("Please enter valid numbers, platform and date.", "error")
        return redirect(url_for("analytics"))
    rows = query("SELECT * FROM metrics WHERE user_id=? ORDER BY record_date DESC, id DESC", (uid,))
    dates = sorted({r["record_date"] for r in rows})
    follower_series = {}
    for p in PLATFORMS:
        by_date = {r["record_date"]: r["followers"] for r in reversed(rows) if r["platform"] == p}
        follower_series[p] = [by_date.get(d) for d in dates]
    totals = {p: {"likes": 0, "clicks": 0} for p in PLATFORMS}
    for r in rows:
        totals[r["platform"]]["likes"] += r["likes"]
        totals[r["platform"]]["clicks"] += r["clicks"]
    chart = {"dates": dates, "followers": follower_series,
             "likes": [totals[p]["likes"] for p in PLATFORMS],
             "clicks": [totals[p]["clicks"] for p in PLATFORMS],
             "platforms": PLATFORMS}
    return render_template("analytics.html", rows=rows, chart=chart,
                           platforms=PLATFORMS, today=date.today().isoformat())


@app.route("/analytics/<int:mid>/delete", methods=["POST"])
@login_required
def delete_metric(mid):
    execute("DELETE FROM metrics WHERE id=? AND user_id=?", (mid, g.user["id"]))
    return redirect(url_for("analytics"))


# ---------- sales ----------
@app.route("/sales", methods=["GET", "POST"])
@login_required
def sales():
    uid = g.user["id"]
    if request.method == "POST":
        action = request.form.get("action")
        try:
            if action == "product":
                name = request.form["name"].strip()
                price = float(request.form["price"])
                if not name or price < 0:
                    raise ValueError
                execute("INSERT INTO products(user_id,name,price,description) VALUES(?,?,?,?)",
                        (uid, name, price, request.form.get("description", "").strip()))
                flash("Product added.", "success")
            elif action == "order":
                pid = int(request.form["product_id"])
                qty = int(request.form.get("quantity") or 1)
                post_id = request.form.get("post_id") or None
                if qty < 1 or not query("SELECT id FROM products WHERE id=? AND user_id=?", (pid, uid), one=True):
                    raise ValueError
                if post_id and not query("SELECT id FROM posts WHERE id=? AND user_id=?", (post_id, uid), one=True):
                    raise ValueError
                execute("""INSERT INTO orders(user_id,product_id,post_id,quantity,order_date)
                    VALUES(?,?,?,?,?)""", (uid, pid, post_id, qty, request.form["order_date"]))
                flash("Order recorded.", "success")
        except (ValueError, KeyError):
            flash("Invalid input. Please check the form.", "error")
        return redirect(url_for("sales"))
    products = query("SELECT * FROM products WHERE user_id=? ORDER BY id DESC", (uid,))
    posts = query("SELECT id,platform,caption FROM posts WHERE user_id=? ORDER BY scheduled_date DESC", (uid,))
    orders = query("""SELECT o.*, p.name pname, p.price, po.platform, po.caption
        FROM orders o JOIN products p ON p.id=o.product_id
        LEFT JOIN posts po ON po.id=o.post_id
        WHERE o.user_id=? ORDER BY o.order_date DESC, o.id DESC""", (uid,))
    by_product = query("""SELECT p.name, COALESCE(SUM(p.price*o.quantity),0) rev
        FROM products p LEFT JOIN orders o ON o.product_id=p.id
        WHERE p.user_id=? GROUP BY p.id""", (uid,))
    by_post = query("""SELECT po.platform, substr(po.caption,1,40) cap,
        SUM(p.price*o.quantity) rev, SUM(o.quantity) qty
        FROM orders o JOIN posts po ON po.id=o.post_id JOIN products p ON p.id=o.product_id
        WHERE o.user_id=? GROUP BY po.id ORDER BY rev DESC LIMIT 5""", (uid,))
    total = sum(o["price"] * o["quantity"] for o in orders)
    chart = {"labels": [r["name"] for r in by_product], "values": [r["rev"] for r in by_product]}
    return render_template("sales.html", products=products, posts=posts, orders=orders,
                           by_post=by_post, total=total, chart=chart, today=date.today().isoformat())


@app.route("/products/<int:pid>/delete", methods=["POST"])
@login_required
def delete_product(pid):
    execute("DELETE FROM orders WHERE product_id=? AND user_id=?", (pid, g.user["id"]))
    execute("DELETE FROM products WHERE id=? AND user_id=?", (pid, g.user["id"]))
    flash("Product and its orders deleted.", "success")
    return redirect(url_for("sales"))


# ---------- public brand page ----------
@app.route("/b/<slug>")
def public_page(slug):
    brand = query("SELECT * FROM brands WHERE slug=?", (slug,), one=True)
    if brand is None:
        abort(404)
    products = query("SELECT * FROM products WHERE user_id=? ORDER BY id DESC", (brand["user_id"],))
    return render_template("public.html", b=brand, products=products)


@app.errorhandler(404)
def not_found(_e):
    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    app.run(debug=True)
