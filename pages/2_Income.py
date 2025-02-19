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


## Chart 1

income_city_summary = filtered_df.groupby("CITY").agg(
    {"HOUSEHOLDS_MEDIAN_INCOME": "mean", "HOUSEHOLDS": "mean"}
).reset_index()

income_bar = alt.Chart(income_city_summary).mark_bar(color="steelblue").encode(
    x=alt.X("CITY:N", title="City"),
    y=alt.Y("HOUSEHOLDS_MEDIAN_INCOME:Q", title="Mean Income ($)", axis=alt.Axis(grid=False)),
    tooltip=["CITY", "HOUSEHOLDS_MEDIAN_INCOME"]
)

household_line = alt.Chart(income_city_summary).mark_line(color="red").encode(
    x=alt.X("CITY:N", title="City"),
    y=alt.Y("HOUSEHOLDS:Q", title="Avg. Households", axis=alt.Axis(grid=True)),
    tooltip=["CITY", "HOUSEHOLDS"]
)

combined_chart = alt.layer(income_bar, household_line).resolve_scale(y="independent").properties(width=900, height=500)

#st.altair_chart(combined_chart, use_container_width=True)

## Heatmap

income_bracket_columns = [
    "HOUSEHOLDS_LESS_THAN_10K", "HOUSEHOLDS_10K_15K", "HOUSEHOLDS_15K_25K", "HOUSEHOLDS_25K_35K", 
    "HOUSEHOLDS_35K_50K", "HOUSEHOLDS_50K_75K", "HOUSEHOLDS_75K_100K", 
    "HOUSEHOLDS_100K_150K", "HOUSEHOLDS_150K_200K", "HOUSEHOLDS_MORE_THAN_200K"
]

renaming_dict = {
    "HOUSEHOLDS_LESS_THAN_10K": "<10K",
    "HOUSEHOLDS_10K_15K": "10K-15K",
    "HOUSEHOLDS_15K_25K": "15K-25K",
    "HOUSEHOLDS_25K_35K": "25K-35K",
    "HOUSEHOLDS_35K_50K": "35K-50K",
    "HOUSEHOLDS_50K_75K": "50K-75K",
    "HOUSEHOLDS_75K_100K": "75K-100K",
    "HOUSEHOLDS_100K_150K": "100K-150K",
    "HOUSEHOLDS_150K_200K": "150K-200K",
    "HOUSEHOLDS_MORE_THAN_200K": "200K+"
}

heatmap_df = filtered_df[["CITY"] + income_bracket_columns].copy()

heatmap_df = heatmap_df.rename(columns=renaming_dict)

heatmap_data = heatmap_df.groupby("CITY")[list(renaming_dict.values())].mean().reset_index()

income_heatmap_long = heatmap_data.melt(id_vars=["CITY"], var_name="Income Bracket", value_name="Percentage")

income_heatmap_long["Percentage"] /= 100  

income_heatmap_long["Income Bracket"] = pd.Categorical(
    income_heatmap_long["Income Bracket"], 
    categories=list(renaming_dict.values()), 
    ordered=True
)

normalized_heatmap = alt.Chart(income_heatmap_long).mark_rect().encode(
    x=alt.X("Income Bracket:N", title="Income Bracket", sort=list(renaming_dict.values())),  
    y=alt.Y("CITY:N", title="City"),
    color=alt.Color("Percentage:Q", scale=alt.Scale(domain=[0,0.35], scheme="blues")),  
    tooltip=["CITY", "Income Bracket", alt.Tooltip("Percentage:Q", format=".2%")]  
).properties(width=900, height=500)

#st.altair_chart(normalized_heatmap, use_container_width=True)

### Chart3

#st.subheader("Income Inequality by City (Box Plot)")

income_boxplot_data = filtered_df[["CITY", "HOUSEHOLDS_MEDIAN_INCOME"]]

income_boxplot = (
    alt.Chart(income_boxplot_data)
    .mark_boxplot(color="white")
    .encode(
        x=alt.X("CITY:N", title="City"),
        y=alt.Y("HOUSEHOLDS_MEDIAN_INCOME:Q", title="Household Median Income ($)"),
        color=alt.Color("CITY:N", legend=None),
        tooltip=["CITY", "HOUSEHOLDS_MEDIAN_INCOME"]
    )
    .properties(width=900, height=500)
)

#st.altair_chart(income_boxplot, use_container_width=True)


## final line chart

#st.subheader("Income Growth Over Time")

income_trend_df = filtered_df.groupby(["YEAR", "CITY"])["HOUSEHOLDS_MEDIAN_INCOME"].median().reset_index()

income_trend_chart = (
    alt.Chart(income_trend_df)
    .mark_line(point=True) 
    .encode(
        x=alt.X("YEAR:O", title="Year"),
        y=alt.Y("HOUSEHOLDS_MEDIAN_INCOME:Q", title="Median Income ($)"),
        color="CITY:N",
        tooltip=["YEAR", "CITY", "HOUSEHOLDS_MEDIAN_INCOME"]
    )
    .properties(width=900, height=500)
)

#st.altair_chart(income_trend_chart, use_container_width=True)

st.title("Income Analysis")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Income Growth Over Time")
    st.altair_chart(income_trend_chart, use_container_width=True)

with col2:
    st.subheader("Income Distribution Heatmap")
    st.altair_chart(normalized_heatmap, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    st.subheader("Mean Income vs Household Count")
    st.altair_chart(combined_chart, use_container_width=True)

with col4:
    st.subheader("Income Inequality by City (Box Plot)")
    st.altair_chart(income_boxplot, use_container_width=True)


