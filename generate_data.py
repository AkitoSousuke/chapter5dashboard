import numpy as np
import pandas as pd
from pathlib import Path

# =========================
# CONFIG
# =========================
SEED = 42
OUT_DIR = Path("./synthetic_license_sales")
OUT_DIR.mkdir(exist_ok=True, parents=True)

rng = np.random.default_rng(SEED)

# =========================
# DIMENSIONS
# =========================
YEARS = [2012, 2013, 2014, 2015, 2016]
QUARTERS = [1, 2, 3, 4]
PRODUCTS = ["Product 1", "Product 2"]
LICENSE_TYPES = ["Invoice", "Maintenance Renewal"]

COUNTRY_REGION = {
    "UK": "EMEA",
    "NO": "EMEA",
    "GR": "EMEA",
    "IT": "EMEA",
    "SP": "EMEA",   # giữ SP để gần giống dashboard
    "LU": "EMEA",
    "US": "North America",
    "DE": "EMEA",
    "FR": "EMEA",
    "SE": "EMEA",
}

COUNTRIES = list(COUNTRY_REGION.keys())

# Trọng số quốc gia để giống country performance trên dashboard
COUNTRY_WEIGHTS = np.array([
    0.28,  # UK
    0.16,  # NO
    0.04,  # GR
    0.03,  # IT
    0.02,  # SP
    0.01,  # LU
    0.26,  # US
    0.08,  # DE
    0.06,  # FR
    0.06,  # SE
], dtype=float)
COUNTRY_WEIGHTS = COUNTRY_WEIGHTS / COUNTRY_WEIGHTS.sum()

COMPANIES = [f"Company {i}" for i in range(1, 151)]

PRODUCT_WEIGHTS = np.array([0.62, 0.38])
LICENSE_WEIGHTS = np.array([0.72, 0.28])

# Tăng trưởng qua các năm để dashboard có xu hướng đẹp
YEAR_SCALE = {
    2012: 0.45,
    2013: 0.65,
    2014: 0.90,
    2015: 1.10,
    2016: 1.25,
}

# Mùa vụ theo quý
QUARTER_SCALE = {
    1: 0.85,
    2: 1.00,
    3: 1.08,
    4: 1.22,
}

# Nhịp tăng theo tuần trong quý (13 tuần)
WEEK_PROFILE = np.array([0.6, 0.7, 0.8, 0.95, 1.15, 1.05, 1.0, 1.08, 1.15, 1.22, 1.3, 1.45, 1.65])

# =========================
# HELPERS
# =========================
def quarter_start_month(q):
    return {1: 1, 2: 4, 3: 7, 4: 10}[q]

def quarter_date_range(year, quarter):
    start_month = quarter_start_month(quarter)
    start = pd.Timestamp(year=year, month=start_month, day=1)
    end = start + pd.offsets.QuarterEnd()
    dates = pd.date_range(start, end, freq="D")
    return start, end, dates

def pick_week_of_quarter(n):
    probs = WEEK_PROFILE / WEEK_PROFILE.sum()
    return rng.choice(np.arange(1, 14), size=n, p=probs)

def week_to_random_date(year, quarter, week_num):
    start, _, _ = quarter_date_range(year, quarter)
    # mỗi tuần ~ 7 ngày, clamp để không vượt cuối quý
    day_offset = min((week_num - 1) * 7 + int(rng.integers(0, 7)), 89)
    return start + pd.Timedelta(days=int(day_offset))

def generate_amount(product, license_type, country, year, quarter):
    base = 0

    # Base theo product và license
    if product == "Product 1":
        base += rng.normal(10500, 2500)
    else:
        base += rng.normal(7200, 1800)

    if license_type == "Maintenance Renewal":
        base *= rng.normal(0.42, 0.06)
    else:
        base *= rng.normal(1.0, 0.08)

    # Country effect
    country_factor = {
        "UK": 1.30, "NO": 1.18, "GR": 0.72, "IT": 0.75, "SP": 0.68,
        "LU": 0.65, "US": 1.35, "DE": 1.05, "FR": 0.98, "SE": 0.92,
    }[country]

    amount = base * country_factor * YEAR_SCALE[year] * QUARTER_SCALE[quarter]

    # Nhiễu
    amount *= rng.normal(1.0, 0.16)
    return max(250, round(amount, 2))

def seat_counts(product, license_type, amount):
    # Số lượng seat gắn với quy mô đơn hàng
    if product == "Product 1":
        admins_mean = amount / 1800
        designers_mean = amount / 2600
        servers_mean = amount / 12000
        sams_mean = amount / 5200
    else:
        admins_mean = amount / 2600
        designers_mean = amount / 2100
        servers_mean = amount / 9000
        sams_mean = amount / 4300

    if license_type == "Maintenance Renewal":
        admins_mean *= 0.55
        designers_mean *= 0.60
        servers_mean *= 0.75
        sams_mean *= 0.70

    admins = max(0, int(rng.poisson(max(admins_mean, 0.2))))
    designers = max(0, int(rng.poisson(max(designers_mean, 0.2))))
    servers = max(0, int(rng.poisson(max(servers_mean, 0.05))))
    sams = max(0, int(rng.poisson(max(sams_mean, 0.05))))

    return admins, designers, servers, sams

def active_client_flag(company_seen_before, license_type):
    # Khách active mới chủ yếu đến từ Invoice
    if company_seen_before:
        return 0
    p = 0.42 if license_type == "Invoice" else 0.10
    return int(rng.random() < p)

# =========================
# GENERATE FACT TABLE
# =========================
rows = []
seen_client_by_quarter = set()
order_seq = 1

for year in YEARS:
    for quarter in QUARTERS:
        # Số transaction/quý tăng theo năm
        expected_tx = int(55 * YEAR_SCALE[year] * QUARTER_SCALE[quarter] * 2.0)
        n_tx = int(max(25, rng.normal(expected_tx, expected_tx * 0.12)))

        weeks = pick_week_of_quarter(n_tx)

        for week in weeks:
            product = rng.choice(PRODUCTS, p=PRODUCT_WEIGHTS)
            license_type = rng.choice(LICENSE_TYPES, p=LICENSE_WEIGHTS)
            country = rng.choice(COUNTRIES, p=COUNTRY_WEIGHTS)
            region = COUNTRY_REGION[country]
            company = rng.choice(COMPANIES)

            order_date = week_to_random_date(year, quarter, int(week))
            amount = generate_amount(product, license_type, country, year, quarter)
            admins, designers, servers, sams = seat_counts(product, license_type, amount)

            quarter_client_key = (year, quarter, company)
            is_new_active_client = active_client_flag(
                company_seen_before=quarter_client_key in seen_client_by_quarter,
                license_type=license_type,
            )
            seen_client_by_quarter.add(quarter_client_key)

            rows.append({
                "order_id": f"ORD-{year}{quarter}-{order_seq:05d}",
                "order_date": order_date,
                "year": year,
                "quarter": f"Q{quarter}",
                "quarter_num": quarter,
                "week_of_quarter": int(week),
                "product": product,
                "license_type": license_type,
                "region": region,
                "country": country,
                "company": company,
                "amount": amount,
                "admins": admins,
                "designers": designers,
                "servers": servers,
                "sams": sams,
                "active_client_flag": is_new_active_client,
            })
            order_seq += 1

sales = pd.DataFrame(rows).sort_values("order_date").reset_index(drop=True)

# =========================
# OPTIONAL TUNING FOR Q2 2016
# để dashboard demo nhìn giống hình hơn
# =========================
mask_q2_2016 = (sales["year"] == 2016) & (sales["quarter_num"] == 2) & (sales["product"] == "Product 1")
sales.loc[mask_q2_2016, "amount"] *= 1.10

# làm tròn sau tuning
sales["amount"] = sales["amount"].round(2)

# =========================
# DERIVED TABLES
# =========================

# 1) Quarterly metrics
quarterly_metrics = (
    sales.groupby(["year", "quarter_num", "quarter"])
    .agg(
        amount=("amount", "sum"),
        transactions=("order_id", "count"),
        active_clients=("active_client_flag", "sum"),
        active_sams=("sams", "sum"),
        designers=("designers", "sum"),
        admins=("admins", "sum"),
        servers=("servers", "sum"),
    )
    .reset_index()
    .sort_values(["year", "quarter_num"])
)

# 2) Last 5 orders
last_orders_sample = (
    sales.sort_values("order_date", ascending=False)
    .loc[:, ["order_date", "company", "country", "product", "license_type", "amount"]]
    .head(5)
    .reset_index(drop=True)
)

# 3) Country performance
country_performance = (
    sales.groupby("country", as_index=False)
    .agg(total_amount=("amount", "sum"))
    .sort_values("total_amount", ascending=False)
)

# 4) Running totals cho Q2 qua các năm
q2 = sales[sales["quarter_num"] == 2].copy()

weekly_q2 = (
    q2.groupby(["year", "week_of_quarter"], as_index=False)
    .agg(weekly_amount=("amount", "sum"))
    .sort_values(["year", "week_of_quarter"])
)

# bảo đảm tuần 1..13 có đủ
all_weeks = pd.DataFrame({"week_of_quarter": np.arange(1, 14)})
running_frames = []

for year in YEARS:
    tmp = all_weeks.merge(
        weekly_q2[weekly_q2["year"] == year],
        on="week_of_quarter",
        how="left"
    )
    tmp["year"] = year
    tmp["weekly_amount"] = tmp["weekly_amount"].fillna(0.0)
    tmp["running_total"] = tmp["weekly_amount"].cumsum()
    running_frames.append(tmp)

running_totals_q2 = pd.concat(running_frames, ignore_index=True)

# 5) KPI snapshot cho 2016 Q2 Product 1, All licenses, All regions
kpi_mask = (
    (sales["year"] == 2016) &
    (sales["quarter_num"] == 2) &
    (sales["product"] == "Product 1")
)
kpi_values = sales.loc[kpi_mask].agg({
    "amount": "sum",
    "order_id": "count",
    "active_client_flag": "sum",
    "sams": "sum",
    "admins": "sum",
    "designers": "sum",
    "servers": "sum"
})

kpi_snapshot = pd.DataFrame({
    "metric": [
        "qtd_sales",
        "qtd_transactions",
        "qtd_active_clients",
        "qtd_sams",
        "admins",
        "designers",
        "servers"
    ],
    "value": [
        kpi_values["amount"],
        kpi_values["order_id"],
        kpi_values["active_client_flag"],
        kpi_values["sams"],
        kpi_values["admins"],
        kpi_values["designers"],
        kpi_values["servers"]
    ]
})

# Days left in quarter giả lập theo ảnh
days_left_eoq = pd.DataFrame([{"metric": "days_left_eoq", "value": 76}])

kpi_snapshot = pd.concat([days_left_eoq, kpi_snapshot], ignore_index=True)

# =========================
# SAVE
# =========================
sales.to_csv(OUT_DIR / "sales_transactions.csv", index=False)
quarterly_metrics.to_csv(OUT_DIR / "quarterly_metrics.csv", index=False)
last_orders_sample.to_csv(OUT_DIR / "last_orders_sample.csv", index=False)
country_performance.to_csv(OUT_DIR / "country_performance.csv", index=False)
running_totals_q2.to_csv(OUT_DIR / "running_totals_q2.csv", index=False)
kpi_snapshot.to_csv(OUT_DIR / "kpi_snapshot.csv", index=False)

print("Done. Files written to:", OUT_DIR.resolve())
print("\nGenerated files:")
for p in sorted(OUT_DIR.glob("*.csv")):
    print("-", p.name)

print("\nSample sales rows:")
print(sales.head(10).to_string(index=False))