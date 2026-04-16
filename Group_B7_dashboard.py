<<<<<<< HEAD
# =========================================
# Nigeria Road Traffic Crash Dashboard (2021–2023)
# Streamlit interactive version
# =========================================

from pathlib import Path

import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px

# ------------------------------
# Page configuration
# ------------------------------
st.set_page_config(
    page_title="Nigeria Road Traffic Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------
# File helpers
# ------------------------------
BASE_DIR = Path(__file__).resolve().parent


def find_existing_file(candidates):
    """Return the first existing file from a list of candidate paths."""
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


# Try both possible Excel filenames
data_candidates = [
    BASE_DIR / "Road_Transport_Data.xlsx",
    BASE_DIR / "Road_Transport Data.xlsx",
]

# Try possible geo file locations
geo_candidates = [
    BASE_DIR / "gadm41_NGA_1.json",
    BASE_DIR / "gadm41_NGA_1.geojson",
    BASE_DIR / "gadm41_NGA_1.json" / "gadm41_NGA_1.json",
    BASE_DIR / "gadm41_NGA_1.json" / "gadm41_NGA_1.geojson",
]

data_file = find_existing_file(data_candidates)
geo_file = find_existing_file(geo_candidates)

if data_file is None:
    st.error("Excel file not found.")
    st.write("Checked these locations:")
    for candidate in data_candidates:
        st.write(str(candidate))
    st.stop()

if geo_file is None:
    st.error("Geo file not found.")
    st.write("Checked these locations:")
    for candidate in geo_candidates:
        st.write(str(candidate))
    st.stop()


# ------------------------------
# Load Data
# ------------------------------
@st.cache_data
def load_excel_data(path):
    return pd.read_excel(path, sheet_name=None)


@st.cache_data
def load_geo_data(path):
    return gpd.read_file(path)


df_dict = load_excel_data(data_file)
states_map = load_geo_data(geo_file)

st.sidebar.success(f"Loaded Excel: {data_file.name}")
st.sidebar.success(f"Loaded Map: {geo_file.name}")

# ------------------------------
# Preprocessing & Aggregation
# ------------------------------

# Aggregate total crashes per state
dfs = []
for sheet, df in df_dict.items():
    if sheet.startswith("RoadCrashes") and sheet != "RoadCrashesmain":
        df = df.copy()
        df = df[df["STATE"].astype(str).str.upper() != "TOTAL"]
        dfs.append(df[["STATE", "TOTAL CASES", "TOTAL CASUALTY"]])

combined_states = pd.concat(dfs, ignore_index=True)

# Fix FCT naming to match GeoJSON
combined_states["STATE"] = combined_states["STATE"].astype(str).str.strip().str.lower()
combined_states["STATE"] = combined_states["STATE"].replace({
    "fct": "federalcapitalterritory",
    "federal capital territory": "federalcapitalterritory"
})

# Aggregate total per state across 3 years
state_totals = (
    combined_states
    .groupby("STATE", as_index=False)[["TOTAL CASES", "TOTAL CASUALTY"]]
    .sum()
    .sort_values("TOTAL CASES", ascending=False)
)

# Merge with GeoJSON
states_map["NAME_1"] = states_map["NAME_1"].astype(str).str.strip().str.lower()
geo_df = states_map.merge(state_totals, left_on="NAME_1", right_on="STATE", how="left")
geo_df["TOTAL CASES"] = geo_df["TOTAL CASES"].fillna(0)
geo_df["TOTAL CASUALTY"] = geo_df["TOTAL CASUALTY"].fillna(0)

# Highest stats for summary cards
highest_state = state_totals.iloc[0]["STATE"].title()
highest_state_cases = int(state_totals.iloc[0]["TOTAL CASES"])

# Crash causes
dfs_cause = []
for sheet, df in df_dict.items():
    if sheet.startswith("CrashCaus"):
        df = df.copy()
        df = df[~df["STATE"].astype(str).str.upper().isin(["TOTAL", "YEAR_TOTAL"])]
        df = df.drop(columns=["STATE", "TOTAL", "QUARTERS_21"], errors="ignore")
        dfs_cause.append(df)

combined_cause = pd.concat(dfs_cause, ignore_index=True)
cause_totals = combined_cause.sum(numeric_only=True).sort_values(ascending=False)
highest_cause = cause_totals.index[0]
highest_cause_value = int(cause_totals.iloc[0])

# Yearly totals from sheet names
trend_records = []
for sheet, df in df_dict.items():
    if sheet.startswith("RoadCrashes") and sheet != "RoadCrashesmain":
        temp = df.copy()
        temp = temp[temp["STATE"].astype(str).str.upper() != "TOTAL"]
        total_cases = temp["TOTAL CASES"].sum()

        # Example expected sheet pattern like RoadCrashes21Q1
        try:
            year = int("20" + sheet[11:13])
        except Exception:
            year = None

        quarter = sheet[-2:] if len(sheet) >= 2 else None
        trend_records.append([year, quarter, total_cases])

trend_df = pd.DataFrame(trend_records, columns=["Year", "Quarter", "Total Cases"])
trend_df = trend_df.dropna(subset=["Year", "Quarter"])

yearly_totals = trend_df.groupby("Year")["Total Cases"].sum().sort_values(ascending=False)
highest_year = int(yearly_totals.index[0])
highest_year_total = int(yearly_totals.iloc[0])

quarterly_totals = trend_df.groupby("Quarter")["Total Cases"].sum().sort_values(ascending=False)
highest_quarter = quarterly_totals.index[0]
highest_quarter_total = int(quarterly_totals.iloc[0])

# ------------------------------
# Sidebar Filters
# ------------------------------
st.sidebar.header("Filters")

# Year slider
year_filter = st.sidebar.slider(
    "Select Year Range:",
    min_value=2021,
    max_value=2023,
    value=(2021, 2023),
    step=1
)

# Quarter slicer
quarter_filter = st.sidebar.multiselect(
    "Select Quarter(s):",
    options=["Q1", "Q2", "Q3", "Q4"],
    default=["Q1", "Q2", "Q3", "Q4"]
)

# High crash states slicer
state_filter = st.sidebar.multiselect(
    "Select High Crash States:",
    options=state_totals["STATE"].tolist(),
    default=state_totals.head(10)["STATE"].tolist()
)

# Map slicer
map_state_filter = st.sidebar.multiselect(
    "Select State(s) for Map:",
    options=state_totals["STATE"].tolist(),
    default=state_totals["STATE"].tolist()
)

# Gender slicer
def get_gender_options(df_dict):
    genders = set()
    for sheet, df in df_dict.items():
        if sheet.startswith(("InjGender", "KillGend")):
            df_clean = df[df["SEX"].astype(str).str.upper() != "TOTAL"].copy()
            df_clean["SEX"] = df_clean["SEX"].astype(str).str.upper().str.strip()
            gender_values = df_clean["SEX"].str.split().str[0].dropna().unique()
            genders.update(gender_values)
    return sorted([g for g in genders if g and g not in ["", "NAN", "NONE"]])


gender_options = get_gender_options(df_dict)
gender_filter = st.sidebar.multiselect(
    "Select Gender:",
    options=gender_options,
    default=gender_options
)

# Vehicle category slicer
category_filter = st.sidebar.multiselect(
    "Select Vehicle Category:",
    options=["GOVERNMENT", "PRIVATE", "COMMERCIAL", "DIPLOMAT"],
    default=["GOVERNMENT", "PRIVATE", "COMMERCIAL", "DIPLOMAT"]
)

# ------------------------------
# Summary Cards
# ------------------------------
st.title("🚦 Nigeria Road Traffic Crash Dashboard (2021–2023)")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("State with Highest Cases", f"{highest_state}", f"{highest_state_cases:,}")
col2.metric("Highest Crash Cause", f"{highest_cause}", f"{highest_cause_value:,}")
col3.metric("Year with Highest Cases", f"{highest_year}", f"{highest_year_total:,}")
col4.metric("Total Cases Across 3 Years", f"{int(state_totals['TOTAL CASES'].sum()):,}")
col5.metric("Total Casualties Across 3 Years", f"{int(state_totals['TOTAL CASUALTY'].sum()):,}")

# ------------------------------
# Quarterly Line Chart
# ------------------------------
st.subheader("📈 Quarterly Road Traffic Crashes")

trend_df = trend_df[
    (trend_df["Year"] >= year_filter[0]) &
    (trend_df["Year"] <= year_filter[1])
].copy()

quarter_order = ["Q1", "Q2", "Q3", "Q4"]
trend_df["Quarter"] = pd.Categorical(trend_df["Quarter"], categories=quarter_order, ordered=True)
trend_df = trend_df[trend_df["Quarter"].isin(quarter_filter)]
trend_df = trend_df.sort_values(["Year", "Quarter"])

fig = px.line(
    trend_df,
    x="Quarter",
    y="Total Cases",
    color="Year",
    markers=True,
    title="Quarterly Road Traffic Crashes"
)
st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# Top 10 States Bar Chart
# ------------------------------
st.subheader("🚨 Top 10 States by Total Crashes")
top10_states = state_totals[state_totals["STATE"].isin(state_filter)].head(10)

fig = px.bar(
    top10_states.sort_values("TOTAL CASES", ascending=True),
    x="TOTAL CASES",
    y="STATE",
    orientation="h",
    text="TOTAL CASES",
    title="Top 10 States by Total Crash Cases"
)
st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# Geospatial Map
# ------------------------------
st.subheader("🗺️ Crash Hotspots Map")
map_geo_df = geo_df[geo_df["STATE"].isin(map_state_filter)].copy()

fig = px.choropleth(
    map_geo_df,
    geojson=map_geo_df.geometry.__geo_interface__,
    locations=map_geo_df.index,
    color="TOTAL CASES",
    hover_name="STATE",
    color_continuous_scale="Reds"
)
fig.update_geos(fitbounds="locations", visible=False)
st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# Gender & Age Group Injuries and Deaths
# ------------------------------
st.subheader("⚠️ Road Traffic Injuries & Deaths by Gender and Age Group")

dfs_inj, dfs_death = [], []

for sheet, df in df_dict.items():
    if sheet.startswith("InjGender"):
        df = df.copy()
        df = df[df["SEX"].astype(str).str.upper() != "TOTAL"]
        df["Year_Total"] = df.filter(like="NUMBER_INJURED").sum(axis=1)
        dfs_inj.append(df[["SEX", "Year_Total"]])

    if sheet.startswith("KillGend"):
        df = df.copy()
        df = df[df["SEX"].astype(str).str.upper() != "TOTAL"]
        df["Year_Total"] = df.filter(like="NUMBER_KILLED").sum(axis=1)
        dfs_death.append(df[["SEX", "Year_Total"]])

gender_inj_df = pd.concat(dfs_inj, ignore_index=True)
gender_death_df = pd.concat(dfs_death, ignore_index=True)

gender_inj_df["SEX"] = gender_inj_df["SEX"].astype(str).str.upper().str.strip()
gender_death_df["SEX"] = gender_death_df["SEX"].astype(str).str.upper().str.strip()

gender_inj_df = gender_inj_df[gender_inj_df["SEX"].str.split().str[0].isin(gender_filter)]
gender_death_df = gender_death_df[gender_death_df["SEX"].str.split().str[0].isin(gender_filter)]

gender_inj = (
    gender_inj_df.groupby("SEX")["Year_Total"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
)

gender_death = (
    gender_death_df.groupby("SEX")["Year_Total"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
)

if not gender_inj.empty:
    fig = px.bar(
        gender_inj,
        x="SEX",
        y="Year_Total",
        text="Year_Total",
        labels={"SEX": "Sex & Age Group", "Year_Total": "Total Injuries"},
        title="Road Traffic Injuries by Gender & Age Group (2021–2023)"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for selected gender(s) in Injuries chart.")

if not gender_death.empty:
    fig = px.bar(
        gender_death,
        x="SEX",
        y="Year_Total",
        text="Year_Total",
        labels={"SEX": "Sex & Age Group", "Year_Total": "Total Deaths"},
        title="Road Traffic Deaths by Gender & Age Group (2021–2023)"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for selected gender(s) in Deaths chart.")

# ------------------------------
# Vehicle Types Pie Charts
# ------------------------------
st.subheader("🚗 Vehicle Types and Categories Involved")

# Vehicle Types
dfs_num = []
for sheet, df in df_dict.items():
    if sheet.startswith("VehNum"):
        df = df.copy()
        df = df[df["VEHICLE CATEGORY"].astype(str).str.upper() != "TOTAL"]
        num_cols = df.filter(like="TYPE_NUM").columns
        df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        df["Year_Total"] = df[num_cols].sum(axis=1)
        dfs_num.append(df[["VEHICLE CATEGORY", "Year_Total"]])

vehicle_type_df = pd.concat(dfs_num, ignore_index=True)
vehicle_type_df["VEHICLE CATEGORY"] = (
    vehicle_type_df["VEHICLE CATEGORY"].astype(str).str.strip().str.upper()
)

vehicle_type_list = sorted(vehicle_type_df["VEHICLE CATEGORY"].unique())
vehicle_type_filter = st.sidebar.multiselect(
    "Select Vehicle Type:",
    options=vehicle_type_list,
    default=vehicle_type_list
)

vehicle_type_df = vehicle_type_df[
    vehicle_type_df["VEHICLE CATEGORY"].isin(vehicle_type_filter)
]

vehicle_totals_num = (
    vehicle_type_df.groupby("VEHICLE CATEGORY")["Year_Total"]
    .sum()
    .sort_values(ascending=False)
)

top7_vehicle_types = vehicle_totals_num.head(7)

fig = px.pie(
    values=top7_vehicle_types.values,
    names=top7_vehicle_types.index,
    title="Top 7 Vehicle Types Distribution",
    color_discrete_sequence=px.colors.qualitative.Bold
)
fig.update_traces(textinfo="percent+label", marker=dict(line=dict(color="black", width=1)))
st.plotly_chart(fig, use_container_width=True)

# Vehicle Categories
dfs_cat = []
main_categories = category_filter

for sheet, df in df_dict.items():
    if sheet.startswith("VehCat"):
        df = df.copy()
        df["VEHICLE CATEGORY"] = df["VEHICLE CATEGORY"].astype(str).str.strip().str.upper()
        df = df[df["VEHICLE CATEGORY"].isin(main_categories)]
        categ_cols = [c for c in df.columns if c.startswith("CATEG_NUM")]
        df[categ_cols] = df[categ_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        df["Year_Total"] = df[categ_cols].sum(axis=1)
        dfs_cat.append(df[["VEHICLE CATEGORY", "Year_Total"]])

vehicle_categories = (
    pd.concat(dfs_cat, ignore_index=True)
    .groupby("VEHICLE CATEGORY")["Year_Total"]
    .sum()
    .sort_values(ascending=False)
)

fig = px.pie(
    values=vehicle_categories.values,
    names=vehicle_categories.index,
    title="Vehicle Categories Distribution",
    color_discrete_sequence=px.colors.qualitative.Vivid
)
fig.update_traces(textinfo="percent+label", marker=dict(line=dict(color="black", width=1)))
=======
# =========================================
# Nigeria Road Traffic Crash Dashboard (2021–2023)
# Streamlit interactive version
# =========================================

from pathlib import Path

import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px

# ------------------------------
# Page configuration
# ------------------------------
st.set_page_config(
    page_title="Nigeria Road Traffic Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------
# File helpers
# ------------------------------
BASE_DIR = Path(__file__).resolve().parent


def find_existing_file(candidates):
    """Return the first existing file from a list of candidate paths."""
    for path in candidates:
        if path.exists() and path.is_file():
            return path
    return None


# Try both possible Excel filenames
data_candidates = [
    BASE_DIR / "Road_Transport_Data.xlsx",
    BASE_DIR / "Road_Transport Data.xlsx",
]

# Try possible geo file locations
geo_candidates = [
    BASE_DIR / "gadm41_NGA_1.json",
    BASE_DIR / "gadm41_NGA_1.geojson",
    BASE_DIR / "gadm41_NGA_1.json" / "gadm41_NGA_1.json",
    BASE_DIR / "gadm41_NGA_1.json" / "gadm41_NGA_1.geojson",
]

data_file = find_existing_file(data_candidates)
geo_file = find_existing_file(geo_candidates)

if data_file is None:
    st.error("Excel file not found.")
    st.write("Checked these locations:")
    for candidate in data_candidates:
        st.write(str(candidate))
    st.stop()

if geo_file is None:
    st.error("Geo file not found.")
    st.write("Checked these locations:")
    for candidate in geo_candidates:
        st.write(str(candidate))
    st.stop()


# ------------------------------
# Load Data
# ------------------------------
@st.cache_data
def load_excel_data(path):
    return pd.read_excel(path, sheet_name=None)


@st.cache_data
def load_geo_data(path):
    return gpd.read_file(path)


df_dict = load_excel_data(data_file)
states_map = load_geo_data(geo_file)

st.sidebar.success(f"Loaded Excel: {data_file.name}")
st.sidebar.success(f"Loaded Map: {geo_file.name}")

# ------------------------------
# Preprocessing & Aggregation
# ------------------------------

# Aggregate total crashes per state
dfs = []
for sheet, df in df_dict.items():
    if sheet.startswith("RoadCrashes") and sheet != "RoadCrashesmain":
        df = df.copy()
        df = df[df["STATE"].astype(str).str.upper() != "TOTAL"]
        dfs.append(df[["STATE", "TOTAL CASES", "TOTAL CASUALTY"]])

combined_states = pd.concat(dfs, ignore_index=True)

# Fix FCT naming to match GeoJSON
combined_states["STATE"] = combined_states["STATE"].astype(str).str.strip().str.lower()
combined_states["STATE"] = combined_states["STATE"].replace({
    "fct": "federalcapitalterritory",
    "federal capital territory": "federalcapitalterritory"
})

# Aggregate total per state across 3 years
state_totals = (
    combined_states
    .groupby("STATE", as_index=False)[["TOTAL CASES", "TOTAL CASUALTY"]]
    .sum()
    .sort_values("TOTAL CASES", ascending=False)
)

# Merge with GeoJSON
states_map["NAME_1"] = states_map["NAME_1"].astype(str).str.strip().str.lower()
geo_df = states_map.merge(state_totals, left_on="NAME_1", right_on="STATE", how="left")
geo_df["TOTAL CASES"] = geo_df["TOTAL CASES"].fillna(0)
geo_df["TOTAL CASUALTY"] = geo_df["TOTAL CASUALTY"].fillna(0)

# Highest stats for summary cards
highest_state = state_totals.iloc[0]["STATE"].title()
highest_state_cases = int(state_totals.iloc[0]["TOTAL CASES"])

# Crash causes
dfs_cause = []
for sheet, df in df_dict.items():
    if sheet.startswith("CrashCaus"):
        df = df.copy()
        df = df[~df["STATE"].astype(str).str.upper().isin(["TOTAL", "YEAR_TOTAL"])]
        df = df.drop(columns=["STATE", "TOTAL", "QUARTERS_21"], errors="ignore")
        dfs_cause.append(df)

combined_cause = pd.concat(dfs_cause, ignore_index=True)
cause_totals = combined_cause.sum(numeric_only=True).sort_values(ascending=False)
highest_cause = cause_totals.index[0]
highest_cause_value = int(cause_totals.iloc[0])

# Yearly totals from sheet names
trend_records = []
for sheet, df in df_dict.items():
    if sheet.startswith("RoadCrashes") and sheet != "RoadCrashesmain":
        temp = df.copy()
        temp = temp[temp["STATE"].astype(str).str.upper() != "TOTAL"]
        total_cases = temp["TOTAL CASES"].sum()

        # Example expected sheet pattern like RoadCrashes21Q1
        try:
            year = int("20" + sheet[11:13])
        except Exception:
            year = None

        quarter = sheet[-2:] if len(sheet) >= 2 else None
        trend_records.append([year, quarter, total_cases])

trend_df = pd.DataFrame(trend_records, columns=["Year", "Quarter", "Total Cases"])
trend_df = trend_df.dropna(subset=["Year", "Quarter"])

yearly_totals = trend_df.groupby("Year")["Total Cases"].sum().sort_values(ascending=False)
highest_year = int(yearly_totals.index[0])
highest_year_total = int(yearly_totals.iloc[0])

quarterly_totals = trend_df.groupby("Quarter")["Total Cases"].sum().sort_values(ascending=False)
highest_quarter = quarterly_totals.index[0]
highest_quarter_total = int(quarterly_totals.iloc[0])

# ------------------------------
# Sidebar Filters
# ------------------------------
st.sidebar.header("Filters")

# Year slider
year_filter = st.sidebar.slider(
    "Select Year Range:",
    min_value=2021,
    max_value=2023,
    value=(2021, 2023),
    step=1
)

# Quarter slicer
quarter_filter = st.sidebar.multiselect(
    "Select Quarter(s):",
    options=["Q1", "Q2", "Q3", "Q4"],
    default=["Q1", "Q2", "Q3", "Q4"]
)

# High crash states slicer
state_filter = st.sidebar.multiselect(
    "Select High Crash States:",
    options=state_totals["STATE"].tolist(),
    default=state_totals.head(10)["STATE"].tolist()
)

# Map slicer
map_state_filter = st.sidebar.multiselect(
    "Select State(s) for Map:",
    options=state_totals["STATE"].tolist(),
    default=state_totals["STATE"].tolist()
)

# Gender slicer
def get_gender_options(df_dict):
    genders = set()
    for sheet, df in df_dict.items():
        if sheet.startswith(("InjGender", "KillGend")):
            df_clean = df[df["SEX"].astype(str).str.upper() != "TOTAL"].copy()
            df_clean["SEX"] = df_clean["SEX"].astype(str).str.upper().str.strip()
            gender_values = df_clean["SEX"].str.split().str[0].dropna().unique()
            genders.update(gender_values)
    return sorted([g for g in genders if g and g not in ["", "NAN", "NONE"]])


gender_options = get_gender_options(df_dict)
gender_filter = st.sidebar.multiselect(
    "Select Gender:",
    options=gender_options,
    default=gender_options
)

# Vehicle category slicer
category_filter = st.sidebar.multiselect(
    "Select Vehicle Category:",
    options=["GOVERNMENT", "PRIVATE", "COMMERCIAL", "DIPLOMAT"],
    default=["GOVERNMENT", "PRIVATE", "COMMERCIAL", "DIPLOMAT"]
)

# ------------------------------
# Summary Cards
# ------------------------------
st.title("🚦 Nigeria Road Traffic Crash Dashboard (2021–2023)")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("State with Highest Cases", f"{highest_state}", f"{highest_state_cases:,}")
col2.metric("Highest Crash Cause", f"{highest_cause}", f"{highest_cause_value:,}")
col3.metric("Year with Highest Cases", f"{highest_year}", f"{highest_year_total:,}")
col4.metric("Total Cases Across 3 Years", f"{int(state_totals['TOTAL CASES'].sum()):,}")
col5.metric("Total Casualties Across 3 Years", f"{int(state_totals['TOTAL CASUALTY'].sum()):,}")

# ------------------------------
# Quarterly Line Chart
# ------------------------------
st.subheader("📈 Quarterly Road Traffic Crashes")

trend_df = trend_df[
    (trend_df["Year"] >= year_filter[0]) &
    (trend_df["Year"] <= year_filter[1])
].copy()

quarter_order = ["Q1", "Q2", "Q3", "Q4"]
trend_df["Quarter"] = pd.Categorical(trend_df["Quarter"], categories=quarter_order, ordered=True)
trend_df = trend_df[trend_df["Quarter"].isin(quarter_filter)]
trend_df = trend_df.sort_values(["Year", "Quarter"])

fig = px.line(
    trend_df,
    x="Quarter",
    y="Total Cases",
    color="Year",
    markers=True,
    title="Quarterly Road Traffic Crashes"
)
st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# Top 10 States Bar Chart
# ------------------------------
st.subheader("🚨 Top 10 States by Total Crashes")
top10_states = state_totals[state_totals["STATE"].isin(state_filter)].head(10)

fig = px.bar(
    top10_states.sort_values("TOTAL CASES", ascending=True),
    x="TOTAL CASES",
    y="STATE",
    orientation="h",
    text="TOTAL CASES",
    title="Top 10 States by Total Crash Cases"
)
st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# Geospatial Map
# ------------------------------
st.subheader("🗺️ Crash Hotspots Map")
map_geo_df = geo_df[geo_df["STATE"].isin(map_state_filter)].copy()

fig = px.choropleth(
    map_geo_df,
    geojson=map_geo_df.geometry.__geo_interface__,
    locations=map_geo_df.index,
    color="TOTAL CASES",
    hover_name="STATE",
    color_continuous_scale="Reds"
)
fig.update_geos(fitbounds="locations", visible=False)
st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# Gender & Age Group Injuries and Deaths
# ------------------------------
st.subheader("⚠️ Road Traffic Injuries & Deaths by Gender and Age Group")

dfs_inj, dfs_death = [], []

for sheet, df in df_dict.items():
    if sheet.startswith("InjGender"):
        df = df.copy()
        df = df[df["SEX"].astype(str).str.upper() != "TOTAL"]
        df["Year_Total"] = df.filter(like="NUMBER_INJURED").sum(axis=1)
        dfs_inj.append(df[["SEX", "Year_Total"]])

    if sheet.startswith("KillGend"):
        df = df.copy()
        df = df[df["SEX"].astype(str).str.upper() != "TOTAL"]
        df["Year_Total"] = df.filter(like="NUMBER_KILLED").sum(axis=1)
        dfs_death.append(df[["SEX", "Year_Total"]])

gender_inj_df = pd.concat(dfs_inj, ignore_index=True)
gender_death_df = pd.concat(dfs_death, ignore_index=True)

gender_inj_df["SEX"] = gender_inj_df["SEX"].astype(str).str.upper().str.strip()
gender_death_df["SEX"] = gender_death_df["SEX"].astype(str).str.upper().str.strip()

gender_inj_df = gender_inj_df[gender_inj_df["SEX"].str.split().str[0].isin(gender_filter)]
gender_death_df = gender_death_df[gender_death_df["SEX"].str.split().str[0].isin(gender_filter)]

gender_inj = (
    gender_inj_df.groupby("SEX")["Year_Total"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
)

gender_death = (
    gender_death_df.groupby("SEX")["Year_Total"]
    .sum()
    .sort_values(ascending=False)
    .reset_index()
)

if not gender_inj.empty:
    fig = px.bar(
        gender_inj,
        x="SEX",
        y="Year_Total",
        text="Year_Total",
        labels={"SEX": "Sex & Age Group", "Year_Total": "Total Injuries"},
        title="Road Traffic Injuries by Gender & Age Group (2021–2023)"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for selected gender(s) in Injuries chart.")

if not gender_death.empty:
    fig = px.bar(
        gender_death,
        x="SEX",
        y="Year_Total",
        text="Year_Total",
        labels={"SEX": "Sex & Age Group", "Year_Total": "Total Deaths"},
        title="Road Traffic Deaths by Gender & Age Group (2021–2023)"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for selected gender(s) in Deaths chart.")

# ------------------------------
# Vehicle Types Pie Charts
# ------------------------------
st.subheader("🚗 Vehicle Types and Categories Involved")

# Vehicle Types
dfs_num = []
for sheet, df in df_dict.items():
    if sheet.startswith("VehNum"):
        df = df.copy()
        df = df[df["VEHICLE CATEGORY"].astype(str).str.upper() != "TOTAL"]
        num_cols = df.filter(like="TYPE_NUM").columns
        df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        df["Year_Total"] = df[num_cols].sum(axis=1)
        dfs_num.append(df[["VEHICLE CATEGORY", "Year_Total"]])

vehicle_type_df = pd.concat(dfs_num, ignore_index=True)
vehicle_type_df["VEHICLE CATEGORY"] = (
    vehicle_type_df["VEHICLE CATEGORY"].astype(str).str.strip().str.upper()
)

vehicle_type_list = sorted(vehicle_type_df["VEHICLE CATEGORY"].unique())
vehicle_type_filter = st.sidebar.multiselect(
    "Select Vehicle Type:",
    options=vehicle_type_list,
    default=vehicle_type_list
)

vehicle_type_df = vehicle_type_df[
    vehicle_type_df["VEHICLE CATEGORY"].isin(vehicle_type_filter)
]

vehicle_totals_num = (
    vehicle_type_df.groupby("VEHICLE CATEGORY")["Year_Total"]
    .sum()
    .sort_values(ascending=False)
)

top7_vehicle_types = vehicle_totals_num.head(7)

fig = px.pie(
    values=top7_vehicle_types.values,
    names=top7_vehicle_types.index,
    title="Top 7 Vehicle Types Distribution",
    color_discrete_sequence=px.colors.qualitative.Bold
)
fig.update_traces(textinfo="percent+label", marker=dict(line=dict(color="black", width=1)))
st.plotly_chart(fig, use_container_width=True)

# Vehicle Categories
dfs_cat = []
main_categories = category_filter

for sheet, df in df_dict.items():
    if sheet.startswith("VehCat"):
        df = df.copy()
        df["VEHICLE CATEGORY"] = df["VEHICLE CATEGORY"].astype(str).str.strip().str.upper()
        df = df[df["VEHICLE CATEGORY"].isin(main_categories)]
        categ_cols = [c for c in df.columns if c.startswith("CATEG_NUM")]
        df[categ_cols] = df[categ_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
        df["Year_Total"] = df[categ_cols].sum(axis=1)
        dfs_cat.append(df[["VEHICLE CATEGORY", "Year_Total"]])

vehicle_categories = (
    pd.concat(dfs_cat, ignore_index=True)
    .groupby("VEHICLE CATEGORY")["Year_Total"]
    .sum()
    .sort_values(ascending=False)
)

fig = px.pie(
    values=vehicle_categories.values,
    names=vehicle_categories.index,
    title="Vehicle Categories Distribution",
    color_discrete_sequence=px.colors.qualitative.Vivid
)
fig.update_traces(textinfo="percent+label", marker=dict(line=dict(color="black", width=1)))
>>>>>>> ba8ca44455f76448d5b01b2d31599bd8aff2db85
st.plotly_chart(fig, use_container_width=True)