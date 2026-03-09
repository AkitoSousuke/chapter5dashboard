import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path

# =========================
# STYLE
# =========================
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
    max-width: 1500px;
}
h1, h2, h3 {
    margin-top: 0.2rem !important;
    margin-bottom: 0.4rem !important;
}
.metric-card {
    background: #f3f3f3;
    border-radius: 4px;
    padding: 10px 12px;
    height: 90px;
    border: 1px solid #e5e5e5;
}
.metric-label {
    font-size: 14px;
    color: #666;
    margin-bottom: 6px;
}
.metric-value {
    font-size: 22px;
    font-weight: 600;
    color: #d07b2d;
}
.panel {
    background: #f7f7f7;
    border: 1px solid #e5e5e5;
    border-radius: 4px;
    padding: 10px;
}
.small-note {
    font-size: 12px;
    color: #777;
}
.report-title {
    font-size: 24px;
    line-height: 1.25;
    font-weight: 600;
    color: #444;
    margin-bottom: 10px;
}
.filter-label {
    font-size: 14px;
    font-weight: 600;
    color: #555;
    margin-top: 8px;
    margin-bottom: 6px;
}
div[data-testid="stDataFrame"] {
    border: none;
}
</style>
""", unsafe_allow_html=True)

# =========================
# LOAD DATA
# =========================
DATA_DIR = Path("./synthetic_license_sales")

@st.cache_data
def load_data():
    sales = pd.read_csv(DATA_DIR / "sales_transactions.csv", parse_dates=["order_date"])
    quarterly_metrics = pd.read_csv(DATA_DIR / "quarterly_metrics.csv")
    last_orders = pd.read_csv(DATA_DIR / "last_orders_sample.csv", parse_dates=["order_date"])
    country_performance = pd.read_csv(DATA_DIR / "country_performance.csv")
    running_totals = pd.read_csv(DATA_DIR / "running_totals_q2.csv")
    return sales, quarterly_metrics, last_orders, country_performance, running_totals

sales, quarterly_metrics, last_orders, country_performance, running_totals = load_data()

# =========================
# HELPERS
# =========================
COLOR_CURRENT = "#b1443a"
COLOR_PREVIOUS = "#f2a29d"
COLOR_PREV_YEAR = "#cc7db6"
COLOR_OLDER = "#d0d0d0"

def format_money(x):
    if pd.isna(x):
        return ""
    if x >= 1_000_000:
        return f"${x/1_000_000:.1f}M"
    if x >= 1_000:
        return f"${x/1_000:.0f}K"
    return f"${x:,.0f}"

def format_money_plain(x):
    return f"{x:,.0f}"

def get_filtered_sales(df, product, license_types, region):
    out = df.copy()
    if product != "All":
        out = out[out["product"] == product]
    if "(All)" not in license_types:
        out = out[out["license_type"].isin(license_types)]
    if region != "All":
        out = out[out["region"] == region]
    return out

def quarter_label(q):
    return f"Q{q}" if isinstance(q, int) else str(q)

def build_running_totals_chart(df_filtered, selected_year=2016, selected_quarter=2):
    subset = df_filtered[df_filtered["quarter_num"] == selected_quarter].copy()

    weekly = (
        subset.groupby(["year", "week_of_quarter"], as_index=False)
        .agg(weekly_amount=("amount", "sum"))
        .sort_values(["year", "week_of_quarter"])
    )

    all_weeks = pd.DataFrame({"week_of_quarter": np.arange(1, 15)})
    lines = []

    years = sorted(subset["year"].unique())
    for year in years:
        tmp = all_weeks.merge(
            weekly[weekly["year"] == year],
            on="week_of_quarter",
            how="left"
        )
        tmp["year"] = year
        tmp["weekly_amount"] = tmp["weekly_amount"].fillna(0)
        tmp["running_total"] = tmp["weekly_amount"].cumsum()
        lines.append(tmp)

    if not lines:
        return go.Figure()

    rt = pd.concat(lines, ignore_index=True)

    prev_q_year = selected_year
    prev_q = selected_quarter - 1
    if prev_q == 0:
        prev_q = 4
        prev_q_year -= 1

    fig = go.Figure()

    # Older
    older_years = [y for y in years if y not in [selected_year, selected_year - 1]]
    for y in older_years:
        d = rt[rt["year"] == y]
        fig.add_trace(go.Scatter(
            x=d["week_of_quarter"],
            y=d["running_total"],
            mode="lines",
            line=dict(color=COLOR_OLDER, width=2),
            name=f"{y} Q{selected_quarter}",
            opacity=0.8,
            hovertemplate=f"{y} Q{selected_quarter}<br>Tuần %{{x}}: $%{{y:,.0f}}<extra></extra>",
            showlegend=False
        ))

    # Previous quarter
    prev_subset = df_filtered[
        (df_filtered["year"] == prev_q_year) &
        (df_filtered["quarter_num"] == prev_q)
    ]
    prev_weekly = (
        prev_subset.groupby("week_of_quarter", as_index=False)
        .agg(weekly_amount=("amount", "sum"))
        .sort_values("week_of_quarter")
    )
    prev_full = all_weeks.merge(prev_weekly, on="week_of_quarter", how="left").fillna(0)
    prev_full["running_total"] = prev_full["weekly_amount"].cumsum()
    fig.add_trace(go.Scatter(
        x=prev_full["week_of_quarter"],
        y=prev_full["running_total"],
        mode="lines",
        line=dict(color=COLOR_PREVIOUS, width=5),
        name="Quý trước",
        hovertemplate="Quý trước<br>Tuần %{x}: $%{y:,.0f}<extra></extra>"
    ))

    # Same quarter previous year
    prev_year_data = rt[rt["year"] == selected_year - 1]
    if not prev_year_data.empty:
        fig.add_trace(go.Scatter(
            x=prev_year_data["week_of_quarter"],
            y=prev_year_data["running_total"],
            mode="lines",
            line=dict(color=COLOR_PREV_YEAR, width=5),
            name=f"Cùng kỳ năm trước",
            hovertemplate=f"{selected_year-1} Q{selected_quarter}<br>Tuần %{{x}}: $%{{y:,.0f}}<extra></extra>"
        ))

    # Current
    curr = rt[rt["year"] == selected_year]
    if not curr.empty:
        fig.add_trace(go.Scatter(
            x=curr["week_of_quarter"],
            y=curr["running_total"],
            mode="lines",
            line=dict(color=COLOR_CURRENT, width=6),
            name="Hiện tại",
            hovertemplate=f"{selected_year} Q{selected_quarter}<br>Tuần %{{x}}: $%{{y:,.0f}}<extra></extra>"
        ))

    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=520,
        paper_bgcolor="#f7f7f7",
        plot_bgcolor="#f7f7f7",
        legend=dict(
            orientation="v",
            x=0.01,
            y=0.99,
            bgcolor="rgba(255,255,255,0)"
        ),
        xaxis=dict(
            title="Tuần thứ",
            showgrid=False,
            tickmode="linear",
            dtick=1,
            zeroline=False
        ),
        yaxis=dict(
            title="",
            gridcolor="#dddddd",
            tickformat="~s",
            zeroline=False
        )
    )
    return fig

def build_quarterly_metric_panel(df_filtered, metric, title, years):
    q = (
        df_filtered.groupby(["year", "quarter_num"], as_index=False)
        .agg(value=(metric, "sum"))
        .sort_values(["year", "quarter_num"])
    )

    fig = go.Figure()
    for year in years:
        d = q[q["year"] == year]
        colors = [COLOR_OLDER] * len(d)

        if year == 2014:
            colors = [COLOR_PREV_YEAR] * len(d)
        elif year == 2015:
            colors = [COLOR_PREVIOUS] * len(d)
        elif year == 2016:
            colors = [COLOR_CURRENT] * len(d)

        fig.add_trace(go.Bar(
            x=[f"{year} Q{i}" for i in d["quarter_num"]],
            y=d["value"],
            marker_color=colors,
            showlegend=False,
            hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>"
        ))

    fig.update_layout(
        height=110,
        margin=dict(l=40, r=10, t=6, b=20),
        paper_bgcolor="#f7f7f7",
        plot_bgcolor="#f7f7f7",
        xaxis=dict(
            showgrid=False,
            showticklabels=False,
            zeroline=False
        ),
        yaxis=dict(
            title=title,
            gridcolor="#dddddd",
            zeroline=False
        )
    )
    return fig

# =========================
# FILTER STATE
# =========================
default_year = 2016
default_quarter = 2

# =========================
# LAYOUT
# =========================
def show_dashboard():
    left, right = st.columns([5.2, 1.2], gap="small")

    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<div class="report-title">BÁO CÁO<br>DOANH SỐ<br>BẢN QUYỀN PHẦN MỀM</div>', unsafe_allow_html=True)

        st.markdown('<div class="filter-label">Sản phẩm</div>', unsafe_allow_html=True)
        # Ánh xạ nhãn tiếng Việt sang giá trị dữ liệu thực tế
        prod_mapping = {"Sản phẩm 1": "Product 1", "Sản phẩm 2": "Product 2", "Tất cả": "All"}
        prod_selection = st.radio(
            "Sản phẩm",
            list(prod_mapping.keys()),
            label_visibility="collapsed",
            index=2 # Mặc định là "Tất cả"
        )
        product = prod_mapping[prod_selection]

        st.markdown('<div class="filter-label">Loại bản quyền (License/MR)</div>', unsafe_allow_html=True)
        license_mapping = {
            "(Tất cả)": "(All)", 
            "Hóa đơn (Invoice)": "Invoice", 
            "Gia hạn (Maintenance Renewal)": "Maintenance Renewal"
        }
        license_selection = st.radio(
            "Loại bản quyền",
            list(license_mapping.keys()),
            label_visibility="collapsed",
            index=0
        )
        license_mode = license_mapping[license_selection]
        selected_license_types = ["(All)"] if license_mode == "(All)" else [license_mode]

        st.markdown('<div class="filter-label">Khu vực</div>', unsafe_allow_html=True)
        region_options = ["All"] + sorted(sales["region"].dropna().unique().tolist())
        # Format lại hàm hiển thị cho selectbox: Nếu là "All" thì hiện "Tất cả", ngược lại giữ nguyên tên Khu vực
        def format_region(r): return "Tất cả" if r == "All" else r
        region = st.selectbox(
            "Khu vực", 
            region_options, 
            format_func=format_region, 
            label_visibility="collapsed"
        )

        filtered_sales = get_filtered_sales(sales, product, selected_license_types, region)

        st.markdown('<div class="filter-label">5 Đơn hàng gần nhất</div>', unsafe_allow_html=True)
        orders_show = (
            filtered_sales.sort_values("order_date", ascending=False)
            .loc[:, ["company", "amount"]]
            .head(5)
            .copy()
        )
        # Sửa lại tên cột khi hiển thị
        orders_show.rename(columns={"company": "Công ty", "amount": "Số tiền"}, inplace=True)
        
        if orders_show.empty:
            st.info("Không có dữ liệu")
        else:
            orders_show["Số tiền"] = orders_show["Số tiền"].map(lambda x: f"$ {x:,.0f}")
            st.dataframe(
                orders_show,
                hide_index=True,
                use_container_width=True,
                height=210
            )

        st.markdown('<div class="filter-label">Hiệu suất theo Quốc gia</div>', unsafe_allow_html=True)
        cp = (
            filtered_sales.groupby("country", as_index=False)
            .agg(total_amount=("amount", "sum"))
            .sort_values("total_amount", ascending=False)
            .head(6)
        )

        if not cp.empty:
            cp = cp.sort_values("total_amount", ascending=True)
            fig_country = go.Figure(go.Bar(
                x=cp["total_amount"],
                y=cp["country"],
                orientation="h",
                marker_color="#5f88b6",
                text=[format_money(v) for v in cp["total_amount"]],
                textposition="outside",
                hovertemplate="%{y}: $%{x:,.0f}<extra></extra>"
            ))
            fig_country.update_layout(
                height=230,
                margin=dict(l=10, r=10, t=0, b=0),
                paper_bgcolor="#f7f7f7",
                plot_bgcolor="#f7f7f7",
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(title="", showgrid=False),
            )
            st.plotly_chart(fig_country, use_container_width=True, config={"displayModeBar": False})

        st.markdown(
            '<div class="small-note">Số tiền hiển thị là khoản tiền đã chuyển cho nhà cung cấp. '
            'Đây là bộ dữ liệu giả lập được xây dựng để mô phỏng dashboard gốc.</div>',
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with left:
        current_q = filtered_sales[
            (filtered_sales["year"] == default_year) &
            (filtered_sales["quarter_num"] == default_quarter)
        ]

        days_left_eoq = 76
        qtd_sales = current_q["amount"].sum()
        qtd_transactions = current_q["order_id"].count()
        qtd_active_clients = current_q["active_client_flag"].sum()
        qtd_sams = current_q["sams"].sum()
        admins = current_q["admins"].sum()
        designers = current_q["designers"].sum()
        servers = current_q["servers"].sum()

        c1, c2, c3, c4 = st.columns(4, gap="small")
        with c1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Số ngày cuối quý</div><div class="metric-value">{days_left_eoq}</div></div>',
                unsafe_allow_html=True
            )
        with c2:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Giao dịch trong quý</div><div class="metric-value" style="color:#555">{qtd_transactions}</div></div>',
                unsafe_allow_html=True
            )
        with c3:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">KH hoạt động trong quý</div><div class="metric-value" style="color:#555">{qtd_active_clients}</div></div>',
                unsafe_allow_html=True
            )
        with c4:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">SAMs trong quý</div><div class="metric-value" style="color:#555">{qtd_sams}</div></div>',
                unsafe_allow_html=True
            )

        c5, c6, c7, c8 = st.columns(4, gap="small")
        with c5:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Doanh số trong quý</div><div class="metric-value">{format_money_plain(qtd_sales)}</div></div>',
                unsafe_allow_html=True
            )
        with c6:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Quản trị viên (Admins)</div><div class="metric-value" style="color:#555">{admins}</div></div>',
                unsafe_allow_html=True
            )
        with c7:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Thiết kế (Designers)</div><div class="metric-value" style="color:#555">{designers}</div></div>',
                unsafe_allow_html=True
            )
        with c8:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">Máy chủ (Servers)</div><div class="metric-value" style="color:#555">{servers}</div></div>',
                unsafe_allow_html=True
            )

        st.markdown("### Doanh số lũy kế (Running Totals)")
        running_fig = build_running_totals_chart(filtered_sales, selected_year=default_year, selected_quarter=default_quarter)
        st.plotly_chart(running_fig, use_container_width=True, config={"displayModeBar": False})

        st.markdown("### Chỉ số hàng quý (Quarterly Metrics)")
        years = sorted(filtered_sales["year"].unique())

        metrics_to_show = [
            ("amount", "Doanh số"),
            ("order_id", "Số lượng giao dịch"),
            ("active_client_flag", "Khách hàng hoạt động"),
            ("sams", "SAMs hoạt động"),
            ("designers", "Thiết kế (Designers)"),
            ("admins", "Quản trị viên (Admins)"),
            ("servers", "Máy chủ (Servers)"),
        ]

        qm_df = filtered_sales.copy()
        qm_df["order_id"] = 1

        for metric, title in metrics_to_show:
            fig = build_quarterly_metric_panel(qm_df, metric, title, years)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})