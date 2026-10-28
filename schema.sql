CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
    brand_name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    bio TEXT,
    niche TEXT,
    logo TEXT,
    instagram TEXT, linkedin TEXT, youtube TEXT, website TEXT
);
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    platform TEXT NOT NULL,
    caption TEXT NOT NULL,
    hashtags TEXT,
    scheduled_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled'
);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    platform TEXT NOT NULL,
    record_date TEXT NOT NULL,
    followers INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    price REAL NOT NULL,
    description TEXT
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    post_id INTEGER REFERENCES posts(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    order_date TEXT NOT NULL
);
