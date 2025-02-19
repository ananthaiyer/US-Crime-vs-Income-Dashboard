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

## Heatmap

import pydeck as pdk
import streamlit as st

st.title("Crime vs. Median Income")

city_list = filtered_df["CITY"].unique().tolist()

city_view_states = {
    "New York": {"lat": 40.7128, "lng": -74.0060, "zoom": 9},
    "Los Angeles": {"lat": 34.0522, "lng": -118.2437, "zoom": 9},
    "Houston": {"lat": 29.7604, "lng": -95.3698, "zoom": 9},
    "Seattle": {"lat": 47.6062, "lng": -122.3321, "zoom": 9},
    "San Francisco": {"lat": 37.7749, "lng": -122.4194, "zoom": 10},  
    "Chicago": {"lat": 41.8781, "lng": -87.6298, "zoom": 9},
}

for city in city_list:
    col1, col2 = st.columns(2)  

    with col1:
        city_crime_data = filtered_df[filtered_df["CITY"] == city].groupby(
            ["ZIP", "LAT", "LNG"], as_index=False
        )["TOTAL_CRIMES"].sum()  

        crime_zip_codes = set(city_crime_data[city_crime_data["TOTAL_CRIMES"] > 0]["ZIP"])

        if not city_crime_data.empty:
            heatmap_crime_layer = pdk.Layer(
                "HeatmapLayer",
                data=city_crime_data,
                get_position=["LNG", "LAT"],
                get_weight="TOTAL_CRIMES",
                radius_pixels=50,  
                intensity=1,
                threshold=0.05,
                opacity = 0.3,
                aggregation="SUM",
            )

            view_state = pdk.ViewState(
                latitude=city_view_states[city]["lat"],
                longitude=city_view_states[city]["lng"],
                zoom=city_view_states[city]["zoom"],  
                pitch=0
            )

            deck_crime = pdk.Deck(
                map_style="mapbox://styles/mapbox/dark-v9",
                initial_view_state=view_state,
                layers=[heatmap_crime_layer],
            )

            st.subheader(f"{city} - Crime")
            st.pydeck_chart(deck_crime)

    with col2:
        city_income_data = filtered_df[filtered_df["CITY"] == city].groupby(
            ["ZIP", "LAT", "LNG"], as_index=False
        )["HOUSEHOLDS_MEDIAN_INCOME"].mean()  

        city_income_data = city_income_data[city_income_data["ZIP"].isin(crime_zip_codes)]

        if not city_income_data.empty:
            heatmap_income_layer = pdk.Layer(
                "HeatmapLayer",
                data=city_income_data,
                get_position=["LNG", "LAT"],
                get_weight="HOUSEHOLDS_MEDIAN_INCOME",  
                radius_pixels=50,  
                intensity=1,
                threshold=0.05,
                opacity = 0.8,
                aggregation="MEAN", 
                color_range=[
                    [50, 50, 215, 90],   # Very low income 
                    [30, 30, 160, 140],  # Low income 
                    [20, 20, 130, 170],  # Medium-low income 
                    [10, 10, 100, 200],  # Medium income 
                    [0, 0, 50, 230],     # High income 
                    [0, 0, 0, 255],   # Very high income
                ]
            )

            deck_income = pdk.Deck(
                map_style="mapbox://styles/mapbox/dark-v9",
                initial_view_state=view_state,
                layers=[heatmap_income_layer],
            )

            st.subheader(f"{city} - Median Income")
            st.pydeck_chart(deck_income)



