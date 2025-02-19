import streamlit as st
import pandas as pd
import altair as alt
from snowflake.snowpark import Session
#from snowflake.snowpark.context import get_active_session
import numpy as np
#import snowflake.connector

import os
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

st.set_page_config(
    page_title="US Income vs Crime Dashboard", 
    layout="wide" 
)
st.markdown("<h1 style='text-align: center;'>US Income vs Crime Dashboard</h1>", unsafe_allow_html=True)
st.title("Key Insights")


@st.cache_resource
def create_session():
    return Session.builder.configs(st.secrets.snowflake).create()

session = create_session()


# Connect to Snowflake


sql_query = "SELECT * FROM US_INCOME.PUBLIC.FINAL_CRIME_WITH_LATLON"
df = session.sql(sql_query).to_pandas()


## DEFAULT
default_year = (int(2018), int(df["YEAR"].max()))
default_month = (1, 12)
default_city = df["CITY"].unique().tolist()
default_offense_category = ["All Categories"] + df["OFFENSE_CATEGORY"].unique().tolist()

## Initializing state
if "selected_year" not in st.session_state:
    st.session_state["selected_year"] = default_year
if "selected_month" not in st.session_state:
    st.session_state["selected_month"] = default_month
if "selected_city" not in st.session_state:
    st.session_state["selected_city"] = default_city
if "selected_offense_category" not in st.session_state:
    st.session_state["selected_offense_category"] = "All Categories"

## Reset filter 
def reset_filters():
    st.session_state["selected_year"] = default_year
    st.session_state["selected_month"] = default_month
    st.session_state["selected_city"] = default_city
    st.session_state["selected_offense_category"] = "All Categories"

### FILTERS, WIDGETS, AND SLIDERS
st.sidebar.title("Filters")
## Sliders for date
selectyear = st.sidebar.slider("Year", int(df["YEAR"].min()), int(df["YEAR"].max()), st.session_state["selected_year"], key="selected_year")
selectmonth = st.sidebar.slider("Month", int(df["MONTH1"].min()), int(df["MONTH1"].max()), st.session_state["selected_month"], key="selected_month")

## City filters
city = st.sidebar.multiselect("Select City", options=df["CITY"].unique(), default=st.session_state["selected_city"], key="selected_city")
off_cat = st.sidebar.selectbox("Select Offense Category", options=default_offense_category, index=0, key="selected_offense_category")

filtered_df = df[
    (df["YEAR"] >= selectyear[0]) & (df["YEAR"] <= selectyear[1]) &
    (df["MONTH1"] >= selectmonth[0]) & (df["MONTH1"] <= selectmonth[1]) &
    (df["CITY"].isin(city)) & 
    ((df["OFFENSE_CATEGORY"].isin(df["OFFENSE_CATEGORY"].unique())) if off_cat == "All Categories" else (df["OFFENSE_CATEGORY"] == off_cat))

]


## Show dataset
if st.sidebar.checkbox('Show table'):
    st.write(filtered_df.head())


st.sidebar.button("Reset Filters", on_click=reset_filters)

## Chart 1


crime_income_data = filtered_df.groupby("CITY").agg(
    {"TOTAL_CRIMES": "sum", "HOUSEHOLDS_MEDIAN_INCOME": "median", "HOUSEHOLDS": "mean"}
).reset_index()

crime_vs_income_scatter = alt.Chart(crime_income_data).mark_circle().encode(
    x=alt.X("HOUSEHOLDS_MEDIAN_INCOME:Q", title="Median Income ($)", scale=alt.Scale(type="log")),
    y=alt.Y("TOTAL_CRIMES:Q", title="Total Crimes", scale=alt.Scale(type="log")),
    size=alt.Size("HOUSEHOLDS:Q", title="Avg Households", scale=alt.Scale(range=[50, 1500])),
    color="CITY:N",
    tooltip=["CITY", "HOUSEHOLDS_MEDIAN_INCOME", "TOTAL_CRIMES", "HOUSEHOLDS"]
).properties(width=900, height=500).interactive()


## Chart 2

crime_income_df = filtered_df.groupby("CITY").agg(
    {"HOUSEHOLDS_MEDIAN_INCOME": "median", "TOTAL_CRIMES": "sum", "HOUSEHOLDS": "mean"}
).reset_index()

crime_income_df["CRIME_RATE_PER_HOUSEHOLD"] = crime_income_df["TOTAL_CRIMES"] / crime_income_df["HOUSEHOLDS"]

crime_rate_min = crime_income_df["CRIME_RATE_PER_HOUSEHOLD"].min()
crime_rate_max = crime_income_df["CRIME_RATE_PER_HOUSEHOLD"].max()
crime_income_df["Crime_Intensity"] = (crime_income_df["CRIME_RATE_PER_HOUSEHOLD"] - crime_rate_min) / (crime_rate_max - crime_rate_min)

color_scale = alt.Scale(domain=[crime_rate_min, crime_rate_max], scheme="reds") 

crime_bar = alt.Chart(crime_income_df).mark_bar().encode(
    x=alt.X("CITY:N", title="City"),
    y=alt.Y("CRIME_RATE_PER_HOUSEHOLD:Q", title="Crime Intensity"),
    color=alt.Color("CRIME_RATE_PER_HOUSEHOLD:Q", scale=color_scale, legend=alt.Legend(title="Crime Intensity")),  
    tooltip=["CITY", "CRIME_RATE_PER_HOUSEHOLD", "HOUSEHOLDS_MEDIAN_INCOME"]
).properties(width=800, height=500)

income_line = alt.Chart(crime_income_df).mark_line(color="white").encode(
    x=alt.X("CITY:N", title="City"),
    y=alt.Y("HOUSEHOLDS_MEDIAN_INCOME:Q", title="Median Income ($)", axis=alt.Axis(grid=True)),
    tooltip=["CITY", "HOUSEHOLDS_MEDIAN_INCOME"]
)

combined_chart = alt.layer(crime_bar, income_line).resolve_scale(y="independent").properties(width=900, height=500)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Crime vs Median Income")
    st.altair_chart(crime_vs_income_scatter, use_container_width=True)


with col2:
    st.subheader("Crime Intensity (Crime Rate per Household)")
    st.altair_chart(combined_chart, use_container_width=True)


### Chart 3

st.subheader("More Income, Less Crime?")

crime_trend = (
    filtered_df.groupby(["CITY", "YEAR", "MONTH1"])
    .agg({"TOTAL_CRIMES": "sum"})
    .reset_index()
)

income_trend = (
    filtered_df.groupby(["CITY", "YEAR"])
    .agg({"HOUSEHOLDS_MEDIAN_INCOME": "median"})
    .reset_index()
)

crime_trend["YEAR_MONTH"] = crime_trend["YEAR"].astype(str) + "-" + crime_trend["MONTH1"].astype(str).str.zfill(2)
income_trend["YEAR_MONTH"] = income_trend["YEAR"].astype(str) + "-01"  # Month 01 for yearly data

income_trend["HOUSEHOLDS_MEDIAN_INCOME_NORM"] = (
    income_trend.groupby("CITY")["HOUSEHOLDS_MEDIAN_INCOME"]
    .transform(lambda x: (x - x.min()) / (x.max() - x.min()))
)

income_trend["INCOME_CHANGE"] = income_trend.groupby("CITY")["HOUSEHOLDS_MEDIAN_INCOME"].diff().fillna(0)
income_filtered = income_trend[income_trend["INCOME_CHANGE"] != 0].copy()

city_monthly_trend = crime_trend.merge(
    income_filtered[["CITY", "YEAR_MONTH", "HOUSEHOLDS_MEDIAN_INCOME", "HOUSEHOLDS_MEDIAN_INCOME_NORM"]],
    on=["CITY", "YEAR_MONTH"],
    how="left"
)

city_monthly_trend["YEAR_MONTH"] = city_monthly_trend["YEAR_MONTH"].astype(str)
city_monthly_trend["TOTAL_CRIMES_NORM"] = (
    city_monthly_trend.groupby("CITY")["TOTAL_CRIMES"]
    .transform(lambda x: (x - x.min()) / (x.max() - x.min()))
)

base = alt.Chart(city_monthly_trend).encode(
    x=alt.X("YEAR_MONTH:O", title="Month-Year")# Use Ordinal (O) for month-year format
)

crime_line = base.mark_line(color="red").encode(
    y=alt.Y("TOTAL_CRIMES_NORM:Q", title="Normalized Crime & Income"),
    tooltip=["CITY", "YEAR_MONTH", "TOTAL_CRIMES"]
)

income_dots = base.mark_circle(color="blue", size=80).encode(
    y=alt.Y("HOUSEHOLDS_MEDIAN_INCOME_NORM:Q"),
    tooltip=["CITY", "YEAR_MONTH", "HOUSEHOLDS_MEDIAN_INCOME"]
)

final_chart = (
    alt.layer(crime_line, income_dots, data=city_monthly_trend).properties(width = 450, height = 300)
    .facet(
        facet=alt.Facet("CITY:N", title="City-wise Monthly Crime vs. Median Income Trends"),
        columns=3,
        spacing=10
    )
    .resolve_scale(y="independent")
)

st.altair_chart(final_chart, use_container_width=True)
