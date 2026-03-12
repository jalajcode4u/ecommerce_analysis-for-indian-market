"""
analysis.py  ·  E-Commerce Sales Analysis
Reads CSVs, answers all 5 questions, saves 6 charts.
Run: python3 analysis.py
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import warnings, os

warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "..", "data")
VIZ  = os.path.join(BASE, "..", "visualizations")
os.makedirs(VIZ, exist_ok=True)

NAVY   = "#1B3A6B"
TEAL   = "#1A7A8A"
ORANGE = "#E85D04"
GREEN  = "#2D6A4F"
PAL    = [NAVY, TEAL, ORANGE, GREEN, "#9B5DE5", "#F72585", "#FFB703"]

sns.set_theme(style="white")
plt.rcParams.update({
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.titlesize":    13,
    "axes.titleweight":  "bold",
    "axes.titlecolor":   NAVY,
    "axes.labelsize":    11,
})

def fmt_inr(x, _): return f"₹{x/1e6:.1f}M"
def save(fig, name):
    fig.savefig(os.path.join(VIZ, name), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✅  {name}")

# ── Load data ─────────────────────────────────────────────────
print("\n📦  Loading data...")
customers  = pd.read_csv(f"{DATA}/customers.csv",  parse_dates=["join_date"])
products   = pd.read_csv(f"{DATA}/products.csv")
orders     = pd.read_csv(f"{DATA}/orders.csv",     parse_dates=["order_date"])
items      = pd.read_csv(f"{DATA}/order_items.csv")

# Merge master table
master = (
    items
    .merge(orders,    on="order_id",   how="left")
    .merge(products,  on="product_id", how="left")
    .merge(customers, on="customer_id",how="left")
)
delivered = master[master["status"] == "Delivered"].copy()

print(f"  Orders: {len(orders):,}  |  Items: {len(items):,}")
print(f"  Revenue (delivered): ₹{delivered['line_total'].sum()/1e6:.2f}M")

# ── Q1: Top Selling Products ──────────────────────────────────
print("\n🔍  Q1 · Top Selling Products")

top_prod = (
    delivered.groupby(["product_name","category"])
    .agg(revenue=("line_total","sum"), units=("quantity","sum"))
    .reset_index().sort_values("revenue", ascending=False).head(12)
)

fig, axes = plt.subplots(1, 2, figsize=(15, 6))
fig.suptitle("Q1 · Top Selling Products", fontsize=15, fontweight="bold", color=NAVY)

# Left: top 10 by revenue
t10 = top_prod.head(10).sort_values("revenue")
cat_colors = {c: PAL[i] for i,c in enumerate(t10["category"].unique())}
bar_colors = [cat_colors[c] for c in t10["category"]]
bars = axes[0].barh(t10["product_name"], t10["revenue"]/1e3, color=bar_colors, height=0.65)
for bar in bars:
    w = bar.get_width()
    axes[0].text(w+50, bar.get_y()+bar.get_height()/2, f"₹{w:.0f}K", va="center", fontsize=8)
axes[0].set_xlabel("Revenue (₹ Thousands)")
axes[0].set_title("Top 10 Products by Revenue")

# Right: top 10 by units sold
t10u = (
    delivered.groupby(["product_name","category"])["quantity"]
    .sum().reset_index().sort_values("quantity", ascending=False).head(10)
)
t10u_sorted = t10u.sort_values("quantity")
axes[1].barh(t10u_sorted["product_name"], t10u_sorted["quantity"],
             color=[cat_colors.get(c, NAVY) for c in t10u_sorted["category"]], height=0.65)
axes[1].set_xlabel("Units Sold")
axes[1].set_title("Top 10 Products by Units Sold")

from matplotlib.patches import Patch
handles = [Patch(facecolor=v, label=k) for k,v in cat_colors.items()]
fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=9,
           title="Category", bbox_to_anchor=(0.5, -0.08), frameon=False)
fig.tight_layout()
save(fig, "Q1_top_products.png")

# ── Q2: Monthly Revenue Trend ─────────────────────────────────
print("🔍  Q2 · Monthly Revenue Trend")

orders["year_month"] = orders["order_date"].dt.to_period("M")
monthly = (
    orders[orders["status"]=="Delivered"]
    .groupby("year_month")
    .agg(revenue=("order_total","sum"), orders=("order_id","count"))
    .reset_index()
)
monthly["yr_mo_str"] = monthly["year_month"].astype(str)
monthly["mom_growth"] = monthly["revenue"].pct_change() * 100
monthly["rolling_3mo"] = monthly["revenue"].rolling(3).mean()

fig, axes = plt.subplots(2, 1, figsize=(14, 9))
fig.suptitle("Q2 · Monthly Revenue Trend", fontsize=15, fontweight="bold", color=NAVY)

xs = range(len(monthly))

# Top: revenue bars + rolling average line
axes[0].bar(xs, monthly["revenue"]/1e6, color=NAVY, alpha=0.8, label="Monthly Revenue")
axes[0].plot(xs, monthly["rolling_3mo"]/1e6, color=ORANGE, lw=2.5, marker="o",
             markersize=4, label="3-Month Rolling Avg")
axes[0].set_xticks(xs[::2])
axes[0].set_xticklabels(monthly["yr_mo_str"].iloc[::2], rotation=45, ha="right", fontsize=8)
axes[0].set_ylabel("Revenue (₹ Millions)")
axes[0].set_title("Monthly Revenue + Rolling Average")
axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(fmt_inr))
axes[0].legend()

# Bottom: MoM growth
colors_mom = [TEAL if g >= 0 else ORANGE for g in monthly["mom_growth"].fillna(0)]
axes[1].bar(xs, monthly["mom_growth"].fillna(0), color=colors_mom, alpha=0.85)
axes[1].axhline(0, color="black", linewidth=0.8, linestyle="--")
axes[1].set_xticks(xs[::2])
axes[1].set_xticklabels(monthly["yr_mo_str"].iloc[::2], rotation=45, ha="right", fontsize=8)
axes[1].set_ylabel("MoM Growth (%)")
axes[1].set_title("Month-over-Month Revenue Growth")

fig.tight_layout(pad=2.5)
save(fig, "Q2_monthly_revenue.png")

# ── Q3: Customer Retention ────────────────────────────────────
print("🔍  Q3 · Customer Retention")

cust_orders = (
    orders[orders["status"].isin(["Delivered","Shipped"])]
    .groupby("customer_id")["order_id"].nunique()
    .reset_index().rename(columns={"order_id":"order_count"})
)
cust_orders["bucket"] = pd.cut(
    cust_orders["order_count"],
    bins=[0,1,3,6,100],
    labels=["1 order\n(One-time)","2–3 orders\n(Returning)","4–6 orders\n(Loyal)","7+ orders\n(Champion)"]
)
bucket_counts = cust_orders["bucket"].value_counts().sort_index()
repeat_rate   = (cust_orders["order_count"] > 1).mean() * 100

# Top 10 customers by LTV
top_customers = (
    orders[orders["status"].isin(["Delivered","Shipped"])]
    .merge(customers[["customer_id","customer_name","segment"]], on="customer_id")
    .groupby(["customer_id","customer_name","segment"])
    .agg(orders_n=("order_id","nunique"), ltv=("order_total","sum"))
    .reset_index().sort_values("ltv", ascending=False).head(10)
)

fig, axes = plt.subplots(1, 3, figsize=(16, 6))
fig.suptitle(f"Q3 · Customer Retention  (Repeat Rate: {repeat_rate:.1f}%)",
             fontsize=15, fontweight="bold", color=NAVY)

# Donut chart
wedge_colors = [NAVY, TEAL, ORANGE, GREEN]
wedges, texts, autos = axes[0].pie(
    bucket_counts, labels=bucket_counts.index,
    autopct="%1.0f%%", colors=wedge_colors,
    startangle=90, pctdistance=0.82,
    wedgeprops=dict(width=0.55, edgecolor="white", linewidth=2)
)
for t in autos: t.set_color("white"); t.set_fontweight("bold"); t.set_fontsize(9)
axes[0].set_title("Customer Order Frequency")

# Top 10 LTV customers
ltv_sorted = top_customers.sort_values("ltv")
seg_colors = {"Regular":NAVY,"Premium":TEAL,"VIP":ORANGE}
bar_c = [seg_colors.get(s,NAVY) for s in ltv_sorted["segment"]]
axes[1].barh(ltv_sorted["customer_name"], ltv_sorted["ltv"]/1e3, color=bar_c, height=0.65)
axes[1].set_xlabel("Lifetime Value (₹ Thousands)")
axes[1].set_title("Top 10 Customers by LTV")

from matplotlib.patches import Patch
axes[1].legend(handles=[Patch(facecolor=v,label=k) for k,v in seg_colors.items()],
               fontsize=8, loc="lower right")

# New vs returning customers monthly
monthly_cohort = orders[orders["status"].isin(["Delivered","Shipped"])].copy()
monthly_cohort["yr_mo"] = monthly_cohort["order_date"].dt.to_period("M")
first_order = monthly_cohort.groupby("customer_id")["order_date"].min().reset_index()
first_order.columns = ["customer_id","first_order_date"]
monthly_cohort = monthly_cohort.merge(first_order, on="customer_id")
monthly_cohort["ctype"] = np.where(
    monthly_cohort["order_date"] == monthly_cohort["first_order_date"], "New", "Returning"
)
cohort_pivot = (
    monthly_cohort.groupby(["yr_mo","ctype"])["customer_id"].nunique()
    .unstack(fill_value=0).reset_index()
)
xc = range(len(cohort_pivot))
axes[2].bar(xc, cohort_pivot.get("New",0), color=TEAL, label="New", alpha=0.85)
axes[2].bar(xc, cohort_pivot.get("Returning",0), bottom=cohort_pivot.get("New",0),
            color=ORANGE, label="Returning", alpha=0.85)
axes[2].set_xticks(list(xc)[::3])
axes[2].set_xticklabels([str(m) for m in cohort_pivot["yr_mo"].iloc[::3]],
                        rotation=45, ha="right", fontsize=8)
axes[2].set_ylabel("Unique Customers")
axes[2].set_title("New vs Returning Customers")
axes[2].legend()

fig.tight_layout()
save(fig, "Q3_customer_retention.png")

# ── Q4: Best Performing Category ─────────────────────────────
print("🔍  Q4 · Best Performing Category")

cat_stats = (
    delivered.groupby("category")
    .agg(
        revenue=("line_total","sum"),
        units=("quantity","sum"),
        orders=("order_id","nunique"),
        avg_discount=("discount_pct","mean"),
    )
    .reset_index()
)
cat_stats["gross_profit"] = delivered.groupby("category").apply(
    lambda x: (x["line_total"] - x["quantity"]*x["cost_price"]).sum()
).values
cat_stats["profit_margin"] = cat_stats["gross_profit"] / cat_stats["revenue"] * 100
cat_stats = cat_stats.sort_values("revenue", ascending=False)

fig, axes = plt.subplots(2, 2, figsize=(13, 10))
fig.suptitle("Q4 · Best Performing Category", fontsize=15, fontweight="bold", color=NAVY)

# TL: revenue bar
cat_rev_sorted = cat_stats.sort_values("revenue", ascending=True)
axes[0,0].barh(cat_rev_sorted["category"], cat_rev_sorted["revenue"]/1e6,
               color=PAL[:len(cat_stats)], height=0.65)
axes[0,0].set_xlabel("Revenue (₹ Millions)")
axes[0,0].set_title("Revenue by Category")

# TR: profit margin
axes[0,1].bar(cat_stats["category"], cat_stats["profit_margin"],
              color=[GREEN if v>35 else ORANGE for v in cat_stats["profit_margin"]], width=0.6)
axes[0,1].set_ylabel("Gross Profit Margin (%)")
axes[0,1].set_title("Profit Margin by Category")
axes[0,1].set_xticklabels(cat_stats["category"], rotation=30, ha="right")
axes[0,1].axhline(cat_stats["profit_margin"].mean(), color="black", ls="--", lw=1, label="Average")
axes[0,1].legend(fontsize=9)

# BL: monthly revenue per category (area chart)
delivered["yr_mo"] = delivered["order_date"].dt.to_period("M")
monthly_cat = (
    delivered.groupby(["yr_mo","category"])["line_total"]
    .sum().unstack(fill_value=0)
)
xm = range(len(monthly_cat))
for i, cat in enumerate(monthly_cat.columns):
    axes[1,0].plot(xm, monthly_cat[cat]/1e6, color=PAL[i], lw=1.8, label=cat)
axes[1,0].set_xticks(list(xm)[::3])
xticklabels = [str(m) for m in monthly_cat.index[::3]]
axes[1,0].set_xticklabels(xticklabels, rotation=45, ha="right", fontsize=7)
axes[1,0].set_ylabel("Revenue (₹ Millions)")
axes[1,0].set_title("Monthly Revenue Trend by Category")
axes[1,0].legend(fontsize=7, ncol=2)

# BR: revenue share donut
axes[1,1].pie(cat_stats["revenue"], labels=cat_stats["category"],
              autopct="%1.0f%%", colors=PAL[:len(cat_stats)],
              startangle=90, pctdistance=0.80,
              wedgeprops=dict(width=0.52, edgecolor="white", linewidth=2))
axes[1,1].set_title("Revenue Share by Category")

fig.tight_layout(pad=2)
save(fig, "Q4_category_performance.png")

# ── Q5: Average Order Value ───────────────────────────────────
print("🔍  Q5 · Average Order Value")

delivered_orders = orders[orders["status"]=="Delivered"]
overall_aov = delivered_orders["order_total"].mean()

aov_segment = (
    delivered_orders.merge(customers[["customer_id","segment"]], on="customer_id")
    .groupby("segment")["order_total"].agg(["mean","count","sum"])
    .reset_index().rename(columns={"mean":"aov","count":"orders","sum":"revenue"})
    .sort_values("aov", ascending=False)
)

aov_payment = (
    delivered_orders.groupby("payment_method")["order_total"]
    .agg(["mean","count"]).reset_index()
    .rename(columns={"mean":"aov","count":"orders"})
    .sort_values("aov", ascending=False)
)

# Basket size analysis
basket = (
    items.merge(orders[orders["status"]=="Delivered"][["order_id","order_total"]], on="order_id")
    .groupby("order_id").agg(item_count=("item_id","count"), total=("order_total","first"))
    .reset_index()
    .groupby("item_count")["total"].mean().reset_index()
    .rename(columns={"total":"aov"})
)

fig, axes = plt.subplots(2, 2, figsize=(13, 10))
fig.suptitle(f"Q5 · Average Order Value  (Overall AOV: ₹{overall_aov:,.0f})",
             fontsize=15, fontweight="bold", color=NAVY)

# TL: AOV by segment
seg_colors_list = [ORANGE if s=="VIP" else (TEAL if s=="Premium" else NAVY)
                   for s in aov_segment["segment"]]
bars = axes[0,0].bar(aov_segment["segment"], aov_segment["aov"],
                     color=seg_colors_list, width=0.5)
for bar in bars:
    axes[0,0].text(bar.get_x()+bar.get_width()/2, bar.get_height()+200,
                   f"₹{bar.get_height():,.0f}", ha="center", fontsize=10, fontweight="bold")
axes[0,0].axhline(overall_aov, color="black", ls="--", lw=1.5, label=f"Overall Avg ₹{overall_aov:,.0f}")
axes[0,0].set_ylabel("Average Order Value (₹)")
axes[0,0].set_title("AOV by Customer Segment")
axes[0,0].legend(fontsize=9)
axes[0,0].set_ylim(0, aov_segment["aov"].max() * 1.25)

# TR: AOV by payment method
axes[0,1].barh(aov_payment["payment_method"], aov_payment["aov"],
               color=NAVY, height=0.5)
axes[0,1].axvline(overall_aov, color=ORANGE, ls="--", lw=1.5)
axes[0,1].set_xlabel("Average Order Value (₹)")
axes[0,1].set_title("AOV by Payment Method")

# BL: Monthly AOV trend
monthly_aov = (
    delivered_orders.groupby(orders["order_date"].dt.to_period("M"))["order_total"]
    .mean().reset_index()
)
monthly_aov["rolling"] = monthly_aov["order_total"].rolling(3).mean()
xv = range(len(monthly_aov))
axes[1,0].plot(xv, monthly_aov["order_total"], color=NAVY, lw=1.5, alpha=0.6, label="Monthly AOV")
axes[1,0].plot(xv, monthly_aov["rolling"], color=ORANGE, lw=2.5, label="3-Mo Rolling Avg")
axes[1,0].set_xticks(list(xv)[::3])
axes[1,0].set_xticklabels([str(m) for m in monthly_aov["order_date"].iloc[::3]],
                          rotation=45, ha="right", fontsize=8)
axes[1,0].set_ylabel("AOV (₹)")
axes[1,0].set_title("Monthly AOV Trend")
axes[1,0].legend()

# BR: Basket size vs AOV
axes[1,1].bar(basket["item_count"], basket["aov"], color=TEAL, width=0.6)
axes[1,1].set_xlabel("Number of Items in Order")
axes[1,1].set_ylabel("Average Order Value (₹)")
axes[1,1].set_title("Basket Size vs Order Value")
axes[1,1].set_xticks(basket["item_count"])

fig.tight_layout(pad=2)
save(fig, "Q5_average_order_value.png")

# ── Executive Dashboard ───────────────────────────────────────
print("🔍  Executive Dashboard")

total_rev    = delivered["line_total"].sum()
total_orders = orders[orders["status"]=="Delivered"]["order_id"].nunique()
repeat_rate2 = (cust_orders["order_count"] > 1).mean() * 100
top_cat      = cat_stats.iloc[0]["category"]

fig = plt.figure(figsize=(16, 10))
fig.patch.set_facecolor("white")
gs  = fig.add_gridspec(3, 4, hspace=0.5, wspace=0.4)

# Title
ax_t = fig.add_subplot(gs[0, :])
ax_t.set_facecolor(NAVY)
ax_t.text(0.5, 0.65, "E-Commerce Sales Analysis — Executive Dashboard",
          ha="center", va="center", fontsize=14, fontweight="bold",
          color="white", transform=ax_t.transAxes)
ax_t.text(0.5, 0.2, "India Market  ·  Jan 2023 – Dec 2024  ·  1,000 Customers  ·  5,000 Orders",
          ha="center", va="center", fontsize=10, color="#A8D8E0", transform=ax_t.transAxes)
ax_t.set_xticks([]); ax_t.set_yticks([])
for s in ax_t.spines.values(): s.set_visible(False)

# KPIs
kpis = [
    (f"₹{total_rev/1e6:.1f}M",  "Total Revenue"),
    (f"{total_orders:,}",        "Orders Delivered"),
    (f"₹{overall_aov:,.0f}",    "Avg Order Value"),
    (f"{repeat_rate2:.1f}%",     "Repeat Rate"),
]
kpi_colors = [NAVY, TEAL, ORANGE, GREEN]
for i, ((val, lbl), col) in enumerate(zip(kpis, kpi_colors)):
    ax = fig.add_subplot(gs[1, i])
    ax.set_facecolor(col)
    ax.text(0.5, 0.60, val, ha="center", va="center", fontsize=20, fontweight="bold",
            color="white", transform=ax.transAxes)
    ax.text(0.5, 0.22, lbl, ha="center", va="center", fontsize=9,
            color="#dddddd", transform=ax.transAxes)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)

# Revenue trend
ax_rev = fig.add_subplot(gs[2, :2])
ax_rev.fill_between(range(len(monthly)), monthly["revenue"]/1e6, alpha=0.2, color=TEAL)
ax_rev.plot(range(len(monthly)), monthly["revenue"]/1e6, color=TEAL, lw=2.5)
ax_rev.set_xticks(range(0, len(monthly), 4))
ax_rev.set_xticklabels(monthly["yr_mo_str"].iloc[::4], rotation=45, ha="right", fontsize=8)
ax_rev.set_title("Monthly Revenue", fontsize=12, fontweight="bold", color=NAVY)
ax_rev.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_inr))
ax_rev.spines["top"].set_visible(False); ax_rev.spines["right"].set_visible(False)

# Category share
ax_cat = fig.add_subplot(gs[2, 2:])
ax_cat.bar(cat_stats["category"], cat_stats["revenue"]/1e6, color=PAL[:len(cat_stats)])
ax_cat.set_ylabel("Revenue (₹M)")
ax_cat.set_title("Revenue by Category", fontsize=12, fontweight="bold", color=NAVY)
ax_cat.set_xticklabels(cat_stats["category"], rotation=30, ha="right", fontsize=8)
ax_cat.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_inr))
ax_cat.spines["top"].set_visible(False); ax_cat.spines["right"].set_visible(False)

save(fig, "Q0_executive_dashboard.png")

# ── Summary ───────────────────────────────────────────────────
print("\n" + "="*55)
print("📊  ANALYSIS SUMMARY")
print("="*55)
print(f"  Total Revenue (Delivered) : ₹{total_rev/1e6:.2f}M")
print(f"  Total Orders              : {total_orders:,}")
print(f"  Overall AOV               : ₹{overall_aov:,.0f}")
print(f"  Repeat Purchase Rate      : {repeat_rate2:.1f}%")
print(f"  Best Category (Revenue)   : {top_cat}")
print(f"  Top Product               : {top_prod.iloc[0]['product_name']}")
print(f"\n  Charts saved to ./visualizations/")
files = sorted(os.listdir(VIZ))
for f in files:
    sz = os.path.getsize(os.path.join(VIZ,f))//1024
    print(f"    · {f}  ({sz} KB)")
