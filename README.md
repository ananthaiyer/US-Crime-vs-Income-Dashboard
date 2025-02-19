# US Income Vs Crime Dashboard

Run Dashboard: [US_Crime_Income_Analysis](https://us-crime-vs-income-dashboard-erlkabpu9zpzn7lidwgb5k.streamlit.app/)

This Streamlit application provides interactive insights into 'crime' and 'income' trends across six major cities in the US.
It integrates Snowflake and Kaggle datasets with visual analytics, and is deployed locally through Docker.

## Features
 - **Key Insights:** Summary of the relationship between crime and income.
 - **Crime:** Explore yearly and monthly crime patterns.
 - **Income:** Compare income distributions between cities.
 - **Heatmaps:** Visualize crime and income density within each city.

 ## Datasets Used
 - **US_Crime:** Monthly crime statistics for the zip codes of 6 major US cities from 2011 to 2021 (Snowflake).
 - **US_Income:** Yearly household income statistics for the zip codes of multiple US cities from 2011 to 2021 (Kaggle: [US_Income](https://www.kaggle.com/datasets/claygendron/us-household-income-by-zip-code-2021-2011))
 - **LATLON:** Latitude and Longitude values for zip codes (Kaggle: [ZIP_LatLon](https://www.kaggle.com/datasets/joeleichter/us-zip-codes-with-lat-and-long))

## Project Structure
Streamlit/

│── Key_Insights.py

│── pages/

│   ├── 1_Crime.py

│   ├── 2_Income.py

│   ├── 3_Heatmaps.py

│── Dockerfile

│── requirements.txt

│── run_app.sh

│── README.md

## Project Setup

### Snowflake

1. Create Warehouse
- Login to 'Snowflake'
- Navigate to 'Admin -> Warehouses -> + Warehouse (top right)'
- Add Warehouse name "US_STATS"
- Click on 'Create Warehouse'

2. Add Databases and Datasets
- **US_Crime:** 
Data Products -> Marketplace -> Search 'US CRIME' -> Get
- **US_Income:** 
*Add Database:* Data -> Databases -> + Database (top right) -> Name "US_INCOME" -> Create
*Add Table:* Data -> Databases -> US_INCOME -> Public -> Create (top right) -> Table -> From File -> Browse local dataset -> Name "INCOME" -> Next -> Load
- **LATLON:** 
*Add Table:* Data -> Databases -> US_INCOME -> Public -> Create (top right) -> Table -> From File -> Browse local dataset -> Name "LATLON" -> Next -> Load

3. Prepare final dataset
Use SQL to combine the final dataset to be used, 'FINAL_CRIME_WITH_LATLON'. It contains data on total monthly crime per zip code with the number of households, percentages of households within different income brackets, mean and median household income, and latitude and longitude of the zip codes.

### Streamlit
1. Create a separate file to contain all the python files that will be a part of the streamlit app. Navigate into the folder on terminal

*bash*
> cd Desktop/Streamlit

2. Set up the coding environment. Open terminal and enter

*bash*
> conda create -n snowpark python=3.8
> conda activate snowpark
> pip install snowflake-snowpark-python streamlit
> conda deactivate

3. Create .streamlit, secrets.toml file, and add access credentials via secrets management

*bash*
> mkdir .streamlit
> touch .streamlit/secrets.toml
> vi .streamlit/secrets.toml

Add the following lines into the secrets file:
- user = "User_Name"
- password = "Password"
- account = "Account_Name"
- warehouse = "Warehouse"
- database = "Database"
- schema = "PUBLIC"

Click Escape -> type ':wq!'

3.1 Store credentials securely
- Use **Streamlit Secrets Management** instead of storing `secrets.toml` locally.
- If using a local `secrets.toml`, add `.streamlit/secrets.toml` to your `.gitignore` file.


4. Create .py files into the folder. To add more pages, create a separate folder as 'pages' and add .py files into the pages.
5. Run Streamlit app locally

*bash*
> streamlit run Key_Insights.py

### Docker

1. Download and install Docker Desktop from [Docker Website](https://docs.docker.com/get-started/get-docker/).
2. Create Docker file in Streamlit Folder

*bash*
> touch Dockerfile

3. Open Docker file and type 

- FROM python:3.12
- WORKDIR /app
- COPY . /app
- RUN pip install --no-cache-dir -r requirements.txt
- EXPOSE 8501
- CMD ["streamlit", "run", "Key_Insights.py"]

4. Create 'requirements.txt' and type

- streamlit
- pandas
- altair
- numpy
- snowflake-snowpark-python

5. Build docker file

*bash*
> docker build -t streamlit-app .

6. Run the app inside Docker

*bash*
> docker run -p 8501:8501 streamlit-app

7. Create shortcut to run it quickly on terminal and open app directly from docker.
- Open terminal and run

*bash*
> nano run_app.sh

- Paste:
> #!/bin/bash
> docker run -p 8501:8501 streamlit-app && open http://localhost:8501

- Save and Exit (CTRL + X, then Y, then Enter)
- Make it executable:
*bash*
> chmod +x run_app.sh

8. Run the shortcut on terminal:
*bash*
> ./run_app.sh

9. Click link on Docker and it opens locally.
Local URL: http://localhost:8501















