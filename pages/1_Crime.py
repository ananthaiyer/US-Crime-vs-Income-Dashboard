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

### CHARTS AND STUFF ###

st.title("Crime Analysis")

import streamlit as st
import altair as alt

## Line chart

filtered_df["YEAR_MONTH"] = filtered_df["YEAR"].astype(str) + "-" + filtered_df["MONTH1"].astype(str).str.zfill(2)
trend1 = filtered_df.groupby(["YEAR_MONTH", "CITY"], as_index=False)["TOTAL_CRIMES"].sum()

chart1 = (
    alt.Chart(trend1)
    .mark_line(point=False)
    .encode(
        x=alt.X("YEAR_MONTH:N", title="Year-Month", sort=alt.SortField("YEAR_MONTH", order="ascending")),
        y=alt.Y("TOTAL_CRIMES:Q", title="Total Crimes"),
        color="CITY:N",
        tooltip=["YEAR_MONTH", "CITY", "TOTAL_CRIMES"]
    )
    .properties(width=400)
    .interactive()
)

col1, col2 = st.columns(2)
with col1:
    st.subheader("Crime Trend Over Time (by City)")
    st.altair_chart(chart1, use_container_width=True)

## Heat map

crime_by_month_city = (
    filtered_df.groupby(["MONTH1", "CITY"], as_index=False)["TOTAL_CRIMES"].sum()
)

crime_by_month_city["NORMALIZED_CRIMES"] = crime_by_month_city.groupby("CITY")["TOTAL_CRIMES"].transform(
    lambda x: (x - x.min()) / (x.max() - x.min())  # Normalize per city
)

crime_heatmap = (
    alt.Chart(crime_by_month_city)
    .mark_rect()
    .encode(
        x=alt.X("MONTH1:O", title="Month", axis=alt.Axis(format="d")),
        y=alt.Y("CITY:N", title="City"),
        color=alt.Color("NORMALIZED_CRIMES:Q", scale=alt.Scale(scheme="reds"), title="Normalized Crimes"),
        tooltip=["MONTH1", "CITY", "TOTAL_CRIMES"]
    )
    .properties(width=800, height=400)
)

with col2:
    st.subheader("Crime Intensity by Month (Normalized)")
    st.altair_chart(crime_heatmap, use_container_width=True)


st.subheader("Total Crime by Offense Category")

## bar chart

crime_by_city = (
    filtered_df.groupby(["CITY", "OFFENSE_CATEGORY"], as_index=False)
    .agg({"TOTAL_CRIMES": "sum"}) 
)

chart2 = (
    alt.Chart(crime_by_city)
    .mark_bar()
    .encode(
        x=alt.X("TOTAL_CRIMES:Q", title="Total Crimes"),
        y=alt.Y("CITY:N", title="City"),  
        color=alt.Color("OFFENSE_CATEGORY:N", title="Offense Category"),
        tooltip=["CITY", "OFFENSE_CATEGORY", "TOTAL_CRIMES"], 
    )
    .properties(width=700, height=400)
    .interactive()
)

col3, col4 = st.columns(2)
with col3:
    st.subheader("Bar Chart")
    st.altair_chart(chart2, use_container_width=True)

## Table chart

table1 = filtered_df.pivot_table(
    values="TOTAL_CRIMES", 
    index="OFFENSE_CATEGORY", 
    columns="CITY", 
    aggfunc="sum", 
    fill_value=0
)

with col4:
    st.subheader("Table")
    st.dataframe(table1)

