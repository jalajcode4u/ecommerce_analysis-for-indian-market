-- ============================================================
--  E-COMMERCE SALES ANALYSIS  ·  Complete SQL Script
--  Database : MySQL 8.0+ / PostgreSQL 14+
--  Author   : Jalaj Kumar
-- ============================================================


-- ============================================================
-- SECTION 1 : DATABASE SCHEMA
-- ============================================================

CREATE DATABASE IF NOT EXISTS ecommerce_db;
USE ecommerce_db;

-- Customers table
CREATE TABLE customers (
    customer_id   VARCHAR(10)  PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    email         VARCHAR(150) UNIQUE NOT NULL,
    city          VARCHAR(50),
    state         VARCHAR(50),
    segment       ENUM('Regular','Premium','VIP') DEFAULT 'Regular',
    join_date     DATE
);

-- Products table
CREATE TABLE products (
    product_id   VARCHAR(10)  PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    category     VARCHAR(50)  NOT NULL,
    price        DECIMAL(10,2) NOT NULL,
    cost_price   DECIMAL(10,2) NOT NULL,
    brand        VARCHAR(50),
    in_stock     TINYINT DEFAULT 1
);

-- Orders table
CREATE TABLE orders (
    order_id       VARCHAR(10)   PRIMARY KEY,
    customer_id    VARCHAR(10)   NOT NULL,
    order_date     DATE          NOT NULL,
    status         ENUM('Delivered','Shipped','Returned','Cancelled') NOT NULL,
    payment_method VARCHAR(20),
    order_total    DECIMAL(12,2) NOT NULL,
    city           VARCHAR(50),
    state          VARCHAR(50),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Order items table (one row per product per order)
CREATE TABLE order_items (
    item_id      VARCHAR(10)   PRIMARY KEY,
    order_id     VARCHAR(10)   NOT NULL,
    product_id   VARCHAR(10)   NOT NULL,
    quantity     INT           NOT NULL DEFAULT 1,
    unit_price   DECIMAL(10,2) NOT NULL,
    discount_pct INT           DEFAULT 0,
    line_total   DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (order_id)   REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- Useful indexes for faster queries
CREATE INDEX idx_orders_date        ON orders(order_date);
CREATE INDEX idx_orders_status      ON orders(status);
CREATE INDEX idx_orders_customer    ON orders(customer_id);
CREATE INDEX idx_items_order        ON order_items(order_id);
CREATE INDEX idx_items_product      ON order_items(product_id);


-- ============================================================
-- SECTION 2 : LOAD DATA  (run after importing CSVs)
-- ============================================================
-- LOAD DATA INFILE '/path/to/customers.csv'   INTO TABLE customers   FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;
-- LOAD DATA INFILE '/path/to/products.csv'    INTO TABLE products    FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;
-- LOAD DATA INFILE '/path/to/orders.csv'      INTO TABLE orders      FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;
-- LOAD DATA INFILE '/path/to/order_items.csv' INTO TABLE order_items FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '\n' IGNORE 1 ROWS;


-- ============================================================
-- SECTION 3 : EXPLORATORY QUERIES  (run first, understand data)
-- ============================================================

-- Row counts in each table
SELECT 'customers'   AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL
SELECT 'products',                  COUNT(*)               FROM products
UNION ALL
SELECT 'orders',                    COUNT(*)               FROM orders
UNION ALL
SELECT 'order_items',               COUNT(*)               FROM order_items;

-- Date range of orders
SELECT
    MIN(order_date) AS first_order,
    MAX(order_date) AS last_order,
    DATEDIFF(MAX(order_date), MIN(order_date)) AS days_covered
FROM orders;

-- Order status breakdown
SELECT
    status,
    COUNT(*)                             AS order_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
FROM orders
GROUP BY status
ORDER BY order_count DESC;

-- Customer segment distribution
SELECT
    segment,
    COUNT(*) AS customer_count
FROM customers
GROUP BY segment;


-- ============================================================
-- SECTION 4 : Q1  ·  TOP SELLING PRODUCTS
-- ============================================================

-- Q1a: Top 10 products by total revenue (delivered orders only)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    SUM(oi.quantity)                       AS units_sold,
    ROUND(SUM(oi.line_total), 0)           AS total_revenue,
    ROUND(AVG(oi.discount_pct), 1)         AS avg_discount_pct,
    ROUND(SUM(oi.line_total) - SUM(oi.quantity * p.cost_price), 0) AS gross_profit
FROM order_items  oi
JOIN orders       o  ON oi.order_id   = o.order_id
JOIN products     p  ON oi.product_id = p.product_id
WHERE o.status = 'Delivered'
GROUP BY p.product_id, p.product_name, p.category
ORDER BY total_revenue DESC
LIMIT 10;

-- Q1b: Top products by units sold (volume leaders)
SELECT
    p.product_name,
    p.category,
    SUM(oi.quantity)  AS units_sold,
    COUNT(DISTINCT oi.order_id) AS order_appearances
FROM order_items  oi
JOIN orders       o  ON oi.order_id   = o.order_id
JOIN products     p  ON oi.product_id = p.product_id
WHERE o.status = 'Delivered'
GROUP BY p.product_id, p.product_name, p.category
ORDER BY units_sold DESC
LIMIT 10;

-- Q1c: Top products ranked within each category  (WINDOW FUNCTION)
SELECT *
FROM (
    SELECT
        p.category,
        p.product_name,
        ROUND(SUM(oi.line_total), 0)   AS revenue,
        SUM(oi.quantity)               AS units_sold,
        RANK() OVER (
            PARTITION BY p.category
            ORDER BY SUM(oi.line_total) DESC
        )                              AS rank_in_category
    FROM order_items  oi
    JOIN orders       o  ON oi.order_id   = o.order_id
    JOIN products     p  ON oi.product_id = p.product_id
    WHERE o.status = 'Delivered'
    GROUP BY p.category, p.product_id, p.product_name
) ranked
WHERE rank_in_category <= 3
ORDER BY category, rank_in_category;


-- ============================================================
-- SECTION 5 : Q2  ·  MONTHLY REVENUE TREND
-- ============================================================

-- Q2a: Month-by-month revenue (delivered orders)
SELECT
    DATE_FORMAT(order_date, '%Y-%m')          AS year_month,
    COUNT(DISTINCT order_id)                  AS orders_placed,
    COUNT(DISTINCT customer_id)               AS unique_customers,
    ROUND(SUM(order_total), 0)                AS monthly_revenue,
    ROUND(AVG(order_total), 0)                AS avg_order_value
FROM orders
WHERE status = 'Delivered'
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY year_month;

-- Q2b: Month-over-month revenue growth  (WINDOW FUNCTION)
WITH monthly_rev AS (
    SELECT
        DATE_FORMAT(order_date, '%Y-%m')  AS yr_mo,
        ROUND(SUM(order_total), 0)        AS revenue
    FROM orders
    WHERE status = 'Delivered'
    GROUP BY DATE_FORMAT(order_date, '%Y-%m')
)
SELECT
    yr_mo,
    revenue,
    LAG(revenue) OVER (ORDER BY yr_mo)                             AS prev_month_revenue,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY yr_mo))
        / LAG(revenue) OVER (ORDER BY yr_mo) * 100
    , 1)                                                           AS mom_growth_pct,
    ROUND(SUM(revenue) OVER (ORDER BY yr_mo), 0)                   AS cumulative_revenue
FROM monthly_rev
ORDER BY yr_mo;

-- Q2c: Quarterly revenue summary with growth
SELECT
    YEAR(order_date)                        AS year,
    QUARTER(order_date)                     AS quarter,
    CONCAT('Q', QUARTER(order_date), '-', YEAR(order_date)) AS label,
    COUNT(DISTINCT order_id)                AS orders,
    ROUND(SUM(order_total), 0)              AS quarterly_revenue,
    ROUND(AVG(order_total), 0)              AS avg_order_value
FROM orders
WHERE status = 'Delivered'
GROUP BY YEAR(order_date), QUARTER(order_date)
ORDER BY year, quarter;

-- Q2d: Revenue by day of week (which day generates most sales)
SELECT
    DAYNAME(order_date)   AS day_of_week,
    DAYOFWEEK(order_date) AS day_num,
    COUNT(*)              AS orders,
    ROUND(SUM(order_total),0) AS revenue
FROM orders
WHERE status = 'Delivered'
GROUP BY DAYNAME(order_date), DAYOFWEEK(order_date)
ORDER BY day_num;


-- ============================================================
-- SECTION 6 : Q3  ·  CUSTOMER RETENTION
-- ============================================================

-- Q3a: How many customers ordered more than once? (Repeat buyers)
SELECT
    order_count_bucket,
    COUNT(*) AS customers
FROM (
    SELECT
        customer_id,
        CASE
            WHEN COUNT(DISTINCT order_id) = 1 THEN '1 order (One-time)'
            WHEN COUNT(DISTINCT order_id) BETWEEN 2 AND 3 THEN '2-3 orders (Returning)'
            WHEN COUNT(DISTINCT order_id) BETWEEN 4 AND 6 THEN '4-6 orders (Loyal)'
            ELSE '7+ orders (Champion)'
        END AS order_count_bucket
    FROM orders
    WHERE status IN ('Delivered','Shipped')
    GROUP BY customer_id
) bucketed
GROUP BY order_count_bucket
ORDER BY FIELD(order_count_bucket,
    '1 order (One-time)',
    '2-3 orders (Returning)',
    '4-6 orders (Loyal)',
    '7+ orders (Champion)');

-- Q3b: Repeat purchase rate
SELECT
    COUNT(DISTINCT customer_id)                     AS total_customers_who_ordered,
    SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_customers,
    ROUND(
        SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) * 100.0
        / COUNT(DISTINCT customer_id), 1
    )                                               AS repeat_rate_pct
FROM (
    SELECT customer_id, COUNT(DISTINCT order_id) AS order_count
    FROM orders
    WHERE status IN ('Delivered','Shipped')
    GROUP BY customer_id
) customer_orders;

-- Q3c: Monthly new vs returning customers  (WINDOW FUNCTION)
WITH first_order AS (
    SELECT customer_id, MIN(order_date) AS first_order_date
    FROM orders
    WHERE status IN ('Delivered','Shipped')
    GROUP BY customer_id
),
monthly_customers AS (
    SELECT
        DATE_FORMAT(o.order_date, '%Y-%m')           AS yr_mo,
        o.customer_id,
        CASE
            WHEN DATE_FORMAT(o.order_date,'%Y-%m')
               = DATE_FORMAT(fo.first_order_date,'%Y-%m')
            THEN 'New'
            ELSE 'Returning'
        END AS customer_type
    FROM orders o
    JOIN first_order fo ON o.customer_id = fo.customer_id
    WHERE o.status IN ('Delivered','Shipped')
)
SELECT
    yr_mo,
    SUM(CASE WHEN customer_type = 'New'       THEN 1 ELSE 0 END) AS new_customers,
    SUM(CASE WHEN customer_type = 'Returning' THEN 1 ELSE 0 END) AS returning_customers,
    COUNT(DISTINCT customer_id)                                    AS total_customers
FROM monthly_customers
GROUP BY yr_mo
ORDER BY yr_mo;

-- Q3d: Top 10 customers by lifetime value  (VIP identification)
SELECT
    c.customer_id,
    c.customer_name,
    c.segment,
    c.city,
    COUNT(DISTINCT o.order_id)            AS total_orders,
    ROUND(SUM(o.order_total), 0)          AS lifetime_value,
    ROUND(AVG(o.order_total), 0)          AS avg_order_value,
    MIN(o.order_date)                     AS first_order,
    MAX(o.order_date)                     AS last_order,
    DATEDIFF(MAX(o.order_date), MIN(o.order_date)) AS days_as_customer
FROM customers  c
JOIN orders     o ON c.customer_id = o.customer_id
WHERE o.status IN ('Delivered','Shipped')
GROUP BY c.customer_id, c.customer_name, c.segment, c.city
ORDER BY lifetime_value DESC
LIMIT 10;

-- Q3e: Customer cohort — retention by join month  (WINDOW FUNCTION)
WITH cohort AS (
    SELECT
        c.customer_id,
        DATE_FORMAT(c.join_date, '%Y-%m')      AS cohort_month,
        DATE_FORMAT(o.order_date, '%Y-%m')     AS order_month
    FROM customers c
    JOIN orders    o ON c.customer_id = o.customer_id
    WHERE o.status IN ('Delivered','Shipped')
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_id) AS cohort_customers
    FROM cohort
    GROUP BY cohort_month
)
SELECT
    cohort.cohort_month,
    cs.cohort_customers,
    COUNT(DISTINCT cohort.customer_id)            AS active_customers,
    ROUND(COUNT(DISTINCT cohort.customer_id) * 100.0
          / cs.cohort_customers, 1)               AS retention_pct
FROM cohort
JOIN cohort_size cs ON cohort.cohort_month = cs.cohort_month
GROUP BY cohort.cohort_month, cs.cohort_customers
ORDER BY cohort.cohort_month;


-- ============================================================
-- SECTION 7 : Q4  ·  BEST PERFORMING CATEGORY
-- ============================================================

-- Q4a: Category performance overview
SELECT
    p.category,
    COUNT(DISTINCT oi.order_id)             AS orders,
    SUM(oi.quantity)                        AS units_sold,
    ROUND(SUM(oi.line_total), 0)            AS total_revenue,
    ROUND(AVG(oi.unit_price), 0)            AS avg_selling_price,
    ROUND(AVG(oi.discount_pct), 1)          AS avg_discount_pct,
    ROUND(SUM(oi.line_total) - SUM(oi.quantity * p.cost_price), 0) AS gross_profit,
    ROUND(
        (SUM(oi.line_total) - SUM(oi.quantity * p.cost_price))
        / SUM(oi.line_total) * 100
    , 1)                                    AS profit_margin_pct
FROM order_items  oi
JOIN orders       o  ON oi.order_id   = o.order_id
JOIN products     p  ON oi.product_id = p.product_id
WHERE o.status = 'Delivered'
GROUP BY p.category
ORDER BY total_revenue DESC;

-- Q4b: Category revenue share  (WINDOW FUNCTION)
SELECT
    category,
    total_revenue,
    ROUND(total_revenue * 100.0 / SUM(total_revenue) OVER (), 1) AS revenue_share_pct,
    RANK() OVER (ORDER BY total_revenue DESC)                     AS revenue_rank
FROM (
    SELECT
        p.category,
        ROUND(SUM(oi.line_total), 0) AS total_revenue
    FROM order_items oi
    JOIN orders      o  ON oi.order_id   = o.order_id
    JOIN products    p  ON oi.product_id = p.product_id
    WHERE o.status = 'Delivered'
    GROUP BY p.category
) cat_rev;

-- Q4c: Monthly revenue breakdown by category  (pivot-style)
SELECT
    DATE_FORMAT(o.order_date, '%Y-%m') AS yr_mo,
    SUM(CASE WHEN p.category = 'Electronics'    THEN oi.line_total ELSE 0 END) AS Electronics,
    SUM(CASE WHEN p.category = 'Clothing'       THEN oi.line_total ELSE 0 END) AS Clothing,
    SUM(CASE WHEN p.category = 'Home & Kitchen' THEN oi.line_total ELSE 0 END) AS Home_Kitchen,
    SUM(CASE WHEN p.category = 'Books'          THEN oi.line_total ELSE 0 END) AS Books,
    SUM(CASE WHEN p.category = 'Sports'         THEN oi.line_total ELSE 0 END) AS Sports,
    SUM(CASE WHEN p.category = 'Beauty'         THEN oi.line_total ELSE 0 END) AS Beauty,
    SUM(CASE WHEN p.category = 'Toys'           THEN oi.line_total ELSE 0 END) AS Toys
FROM order_items oi
JOIN orders      o  ON oi.order_id   = o.order_id
JOIN products    p  ON oi.product_id = p.product_id
WHERE o.status = 'Delivered'
GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
ORDER BY yr_mo;


-- ============================================================
-- SECTION 8 : Q5  ·  AVERAGE ORDER VALUE (AOV)
-- ============================================================

-- Q5a: Overall AOV
SELECT
    COUNT(DISTINCT order_id)         AS total_orders,
    ROUND(SUM(order_total), 0)       AS total_revenue,
    ROUND(AVG(order_total), 0)       AS avg_order_value,
    ROUND(MIN(order_total), 0)       AS min_order_value,
    ROUND(MAX(order_total), 0)       AS max_order_value,
    ROUND(STDDEV(order_total), 0)    AS std_dev
FROM orders
WHERE status = 'Delivered';

-- Q5b: AOV by customer segment  (key business insight)
SELECT
    c.segment,
    COUNT(DISTINCT o.order_id)           AS orders,
    ROUND(AVG(o.order_total), 0)         AS avg_order_value,
    ROUND(SUM(o.order_total), 0)         AS total_revenue,
    ROUND(AVG(o.order_total) / (
        SELECT AVG(order_total) FROM orders WHERE status = 'Delivered'
    ) * 100, 0)                          AS index_vs_overall
FROM orders     o
JOIN customers  c ON o.customer_id = c.customer_id
WHERE o.status = 'Delivered'
GROUP BY c.segment
ORDER BY avg_order_value DESC;

-- Q5c: AOV by payment method
SELECT
    payment_method,
    COUNT(*)                          AS orders,
    ROUND(AVG(order_total), 0)        AS avg_order_value,
    ROUND(SUM(order_total), 0)        AS total_revenue
FROM orders
WHERE status = 'Delivered'
GROUP BY payment_method
ORDER BY avg_order_value DESC;

-- Q5d: Monthly AOV trend with moving average  (WINDOW FUNCTION)
WITH monthly_aov AS (
    SELECT
        DATE_FORMAT(order_date, '%Y-%m')  AS yr_mo,
        ROUND(AVG(order_total), 0)        AS monthly_aov,
        COUNT(*)                          AS orders
    FROM orders
    WHERE status = 'Delivered'
    GROUP BY DATE_FORMAT(order_date, '%Y-%m')
)
SELECT
    yr_mo,
    orders,
    monthly_aov,
    ROUND(AVG(monthly_aov) OVER (
        ORDER BY yr_mo
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 0)                               AS rolling_3mo_avg_aov
FROM monthly_aov
ORDER BY yr_mo;

-- Q5e: AOV by number of items in order  (basket size analysis)
SELECT
    item_count,
    COUNT(*)                       AS orders,
    ROUND(AVG(order_total), 0)     AS avg_order_value
FROM (
    SELECT
        o.order_id,
        o.order_total,
        COUNT(oi.item_id)          AS item_count
    FROM orders      o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status = 'Delivered'
    GROUP BY o.order_id, o.order_total
) order_sizes
GROUP BY item_count
ORDER BY item_count;


-- ============================================================
-- SECTION 9 : BONUS  ·  ADVANCED ANALYSIS
-- ============================================================

-- BONUS 1: RFM Segmentation  (Recency · Frequency · Monetary)
-- The gold standard for customer analysis in DA interviews
WITH rfm_raw AS (
    SELECT
        customer_id,
        DATEDIFF('2025-01-01', MAX(order_date)) AS recency_days,
        COUNT(DISTINCT order_id)                AS frequency,
        ROUND(SUM(order_total), 0)              AS monetary
    FROM orders
    WHERE status IN ('Delivered','Shipped')
    GROUP BY customer_id
),
rfm_scores AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,  -- lower days = better
        NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
    FROM rfm_raw
)
SELECT
    customer_id,
    recency_days,
    frequency,
    monetary,
    r_score, f_score, m_score,
    (r_score + f_score + m_score) AS total_rfm_score,
    CASE
        WHEN (r_score + f_score + m_score) >= 13 THEN 'Champion'
        WHEN (r_score + f_score + m_score) >= 10 THEN 'Loyal'
        WHEN (r_score + f_score + m_score) >= 7  THEN 'At Risk'
        ELSE 'Lost'
    END                            AS rfm_segment
FROM rfm_scores
ORDER BY total_rfm_score DESC
LIMIT 20;

-- BONUS 2: Product pairs most often bought together
SELECT
    a.product_id  AS product_1,
    b.product_id  AS product_2,
    pa.product_name AS name_1,
    pb.product_name AS name_2,
    COUNT(*)       AS times_bought_together
FROM order_items  a
JOIN order_items  b  ON a.order_id   = b.order_id
                    AND a.product_id < b.product_id   -- avoid duplicates
JOIN products     pa ON a.product_id = pa.product_id
JOIN products     pb ON b.product_id = pb.product_id
GROUP BY a.product_id, b.product_id, pa.product_name, pb.product_name
ORDER BY times_bought_together DESC
LIMIT 10;

-- BONUS 3: Running total revenue per customer  (WINDOW FUNCTION)
SELECT
    customer_id,
    order_date,
    order_total,
    SUM(order_total) OVER (
        PARTITION BY customer_id
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_spend
FROM orders
WHERE status IN ('Delivered','Shipped')
ORDER BY customer_id, order_date
LIMIT 30;

-- BONUS 4: State-wise revenue ranking
SELECT
    state,
    COUNT(DISTINCT customer_id)          AS customers,
    COUNT(DISTINCT order_id)             AS orders,
    ROUND(SUM(order_total), 0)           AS revenue,
    ROUND(AVG(order_total), 0)           AS avg_order_value,
    RANK() OVER (ORDER BY SUM(order_total) DESC) AS revenue_rank
FROM orders
WHERE status = 'Delivered'
GROUP BY state
ORDER BY revenue DESC;
