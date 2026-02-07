import streamlit as st
import pandas as pd
import plotly.express as px

# Mapeo básico Estado (nombre) -> abreviatura (para mapa USA).
# Si tu dataset ya trae abreviaturas (CA, NY, etc.), no lo necesitás.
US_STATE_TO_CODE = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI",
    "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
}

REQUIRED_COLS = [
    "Order Date", "Ship Date", "Category", "Sub-Category",
    "Sales", "Profit", "Region", "State", "Quantity"
]

@st.cache_data
def load_and_clean(csv_file) -> pd.DataFrame:
    df = pd.read_csv(csv_file)

    # 1) Validación: están las columnas necesarias?
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {missing}")

    # 2) Fechas a datetime
    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], errors="coerce")

    # 3) Nulos + duplicados
    df = df.drop_duplicates()
    df = df.dropna(subset=["Order Date", "Sales", "Profit", "State"])

    # 4) Year desde Order Date
    df["Year"] = df["Order Date"].dt.year

    # 5) Asegurar numéricos
    df["Sales"] = pd.to_numeric(df["Sales"], errors="coerce")
    df["Profit"] = pd.to_numeric(df["Profit"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")

    df = df.dropna(subset=["Sales", "Profit", "Quantity"])

    # 6) Estado a código (para choropleth USA)
    #    Si ya viene como "CA", "NY", etc., se mantiene.
    df["StateCode"] = df["State"].map(US_STATE_TO_CODE).fillna(df["State"])

    return df

st.set_page_config(page_title="Proyecto #3 - Dashboard", layout="wide")
st.title("📊 Proyecto #3 — Dashboard de Ventas y Profit")

st.write(
    "Subí un CSV con columnas: "
    "`Order Date`, `Ship Date`, `Category`, `Sub-Category`, `Sales`, `Profit`, "
    "`Region`, `State`, `Quantity`"
)

uploaded = st.file_uploader("📁 Subí tu archivo CSV", type=["csv"])
if not uploaded:
    st.stop()

try:
    df = load_and_clean(uploaded)
except Exception as e:
    st.error(f"Error al cargar/limpiar el dataset: {e}")
    st.stop()

# ---------------------------
# Filtros (interactivos)
# ---------------------------
with st.sidebar:
    st.header("Filtros")

    all_regions = sorted(df["Region"].dropna().unique())
    selected_regions = st.multiselect("Region", options=all_regions, default=all_regions)

    all_categories = sorted(df["Category"].dropna().unique())
    selected_categories = st.multiselect("Category", options=all_categories, default=all_categories)

    min_date = df["Order Date"].min().date()
    max_date = df["Order Date"].max().date()
    date_range = st.date_input("Rango de fechas (Order Date)", value=(min_date, max_date))

# aplicar filtros
filtered = df.copy()
filtered = filtered[filtered["Region"].isin(selected_regions)]
filtered = filtered[filtered["Category"].isin(selected_categories)]

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    filtered = filtered[(filtered["Order Date"].dt.date >= start) & (filtered["Order Date"].dt.date <= end)]

# ---------------------------
# KPIs
# ---------------------------
kpi1, kpi2, kpi3 = st.columns(3)
kpi1.metric("💰 Ventas (Sales)", f"{filtered['Sales'].sum():,.0f}")
kpi2.metric("✅ Profit", f"{filtered['Profit'].sum():,.0f}")
kpi3.metric("📦 Cantidad (Quantity)", f"{filtered['Quantity'].sum():,.0f}")

st.divider()

# ---------------------------
# EDA 1: Ventas & Profit por año
# ---------------------------
yearly = filtered.groupby("Year", as_index=False)[["Sales", "Profit"]].sum()

c1, c2 = st.columns(2)
with c1:
    fig_sales_year = px.line(yearly, x="Year", y="Sales", markers=True, title="Ventas por año")
    st.plotly_chart(fig_sales_year, use_container_width=True)

with c2:
    fig_profit_year = px.line(yearly, x="Year", y="Profit", markers=True, title="Profit por año")
    st.plotly_chart(fig_profit_year, use_container_width=True)

st.divider()

# ---------------------------
# EDA 2: Top 5 Sub-Categories por ventas
# ---------------------------
top5 = (
    filtered.groupby("Sub-Category", as_index=False)["Sales"].sum()
    .sort_values("Sales", ascending=False)
    .head(5)
)

fig_top5 = px.bar(top5, x="Sales", y="Sub-Category", orientation="h", title="Top 5 Sub-Categories por Ventas")
st.plotly_chart(fig_top5, use_container_width=True)

st.divider()

# ---------------------------
# Mapa: Ventas por Estado (USA choropleth)
# ---------------------------
by_state = filtered.groupby("StateCode", as_index=False)["Sales"].sum()

fig_map = px.choropleth(
    by_state,
    locations="StateCode",
    locationmode="USA-states",
    color="Sales",
    scope="usa",
    title="Ventas por Estado (USA)"
)
st.plotly_chart(fig_map, use_container_width=True)

# ---------------------------
# Tabla final (para inspección)
# ---------------------------
st.subheader("🔎 Muestra del dataset filtrado")
st.dataframe(filtered.head(50))
