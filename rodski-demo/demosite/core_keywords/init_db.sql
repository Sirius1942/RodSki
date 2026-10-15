-- 电商管理系统数据库

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no TEXT NOT NULL UNIQUE,
    customer_name TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    customer_address TEXT,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_no TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    stock INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    total_orders INTEGER DEFAULT 0,
    total_amount DECIMAL(10,2) DEFAULT 0
);

INSERT INTO orders (order_no, customer_name, customer_phone, product_name, quantity, price, total_amount, status) VALUES
('ORD202403230001', '张伟', '13800138001', 'iPhone 15 Pro 256GB', 1, 8999.00, 8999.00, 'paid'),
('ORD202403230002', '李娜', '13800138002', '戴森吹风机', 1, 2990.00, 2990.00, 'shipped'),
('ORD202403230003', '王强', '13800138003', 'AirPods Pro 2', 1, 1899.00, 1899.00, 'completed');

INSERT INTO products (product_no, name, category, price, stock) VALUES
('P001', 'iPhone 15 Pro 256GB', '手机', 8999.00, 45),
('P002', '戴森吹风机', '家电', 2990.00, 23),
('P003', 'AirPods Pro 2', '数码配件', 1899.00, 120);

INSERT INTO customers (customer_id, name, phone, email, total_orders, total_amount) VALUES
('C001', '张伟', '13800138001', 'zhangwei@example.com', 15, 45680.00),
('C002', '李娜', '13800138002', 'lina@example.com', 8, 23450.00),
('C003', '王强', '13800138003', 'wangqiang@example.com', 12, 38900.00);
