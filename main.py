import requests as rq
import logging
from flask import Flask, request, jsonify, Response
import anthropic
import base64
import httpx
import ollama                                                                                                                                                                               
import os
import random
import uuid
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry

BASEURL = os.getcwd()
API_KEY = '<API_KEY_HERE>'

def get_all_text(user_id, *args):
    text = ""
    args = args[0]
    for arg in args:
        arg = f'{BASEURL}/outputs/{user_id}/' + arg
        print(arg)
        with open(arg, "r") as f:
            text += f.read()
            text += "\n"
            print(text)
    return text

app = Flask(__name__)
client = anthropic.Client(api_key=API_KEY)
app.config['SECRET_KEY'] = 'secret!'

@app.post("/get-weather")
def weather():
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
    retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
    openmeteo = openmeteo_requests.Client(session = retry_session)

    latitude = request.json.get("latitude")
    longitude = request.json.get("longitude")
    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/gfs"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation", "surface_pressure", "wind_speed_10m"]
    }
    responses = openmeteo.weather_api(url, params=params)

    # Process first location. Add a for-loop for multiple locations or weather models
    response = responses[0]
    print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
    print(f"Elevation {response.Elevation()} m asl")
    print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
    print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
    hourly_apparent_temperature = hourly.Variables(2).ValuesAsNumpy()
    hourly_precipitation = hourly.Variables(3).ValuesAsNumpy()
    hourly_surface_pressure = hourly.Variables(4).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(5).ValuesAsNumpy()

    hourly_data = {"date": pd.date_range(
        start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
        end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
        freq = pd.Timedelta(seconds = hourly.Interval()),
        inclusive = "left"
    )}
    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["relative_humidity_2m"] = hourly_relative_humidity_2m
    hourly_data["apparent_temperature"] = hourly_apparent_temperature
    hourly_data["precipitation"] = hourly_precipitation
    hourly_data["surface_pressure"] = hourly_surface_pressure
    hourly_data["wind_speed_10m"] = hourly_wind_speed_10m

    hourly_dataframe = pd.DataFrame(data = hourly_data)
    print(hourly_dataframe)
    return jsonify(hourly_dataframe.to_dict(orient="records"))


@app.post("/soil-data")
def get_ambee_soil_data():
    """Fetches soil data from Ambee API.

    Args:
        api_key: Your Ambee API key.
        latitude: Latitude of the location.
        longitude: Longitude of the location.

    Returns:
        A dictionary containing soil data if successful, or None if an error occurs.
    """
    latitude = request.json.get("latitude")
    longitude = request.json.get("longitude")

    base_url = "https://api.ambeedata.com/latest/by-lat-lng?lat=12&lng=77"
    params = {
        "lat": latitude,
        "lng": longitude
    }

    headers = {
        "x-api-key": "80debf38b52a7b5df23570b37b30f2b19bac562338653710069ed39c7e11d74a",
        "Content-type": "application/json" 
    }

    try:
        response = rq.get(base_url, params=params, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        return data
    except rq.exceptions.RequestException as e:
        print(f"Error fetching soil data: {e}")
        return None
    
    print(data)

    # # Example usage:
    # api_key = "80debf38b52a7b5df23570b37b30f2b19bac562338653710069ed39c7e11d74a"  # Replace with your actual API key
    # # latitude = 40.7128 
    # # longitude = -74.0060
    # soil_data = get_ambee_soil_data(api_key, latitude, longitude)

    # if soil_data:
    #     print(soil_data)


@app.post("/crop-detail")
def generate():
    messages_str = request.json.get("messages")
    uid = request.json.get("uid")
    previous_messages =""
    # create_medical_summary(uid)
    if not os.path.exists("outputs"):
        os.mkdir("outputs")
    if not os.path.exists(f"outputs/{uid}"):
        os.mkdir(f"outputs/{uid}")
    with open(f"outputs/{uid}/medical_summary.txt", "a+") as f:
        previous_messages = f.read()
    
    messages = f"Previous Chat : {previous_messages}\n\nCurrent Question : {messages_str}"
    system_prompt = """You are Sage, a sustainability-focused agricultural consultant. You possess a vast knowledge of sustainable farming practices and regional ecosystems. You prioritize data-driven analysis for informed decision-making. You excel at interpreting GIS data and translating it into actionable recommendations. Given a JSON file containing the following agricultural data: Location: Specific coordinates (latitude and longitude) Soil Properties: pH, nutrient levels (nitrogen, phosphorus, potassium), organic matter content Climate Data: Average temperature, rainfall patterns, sunlight hours Elevation: Height above sea level Sage should analyze the data and provide a comprehensive response including: Suitable Crop Recommendations: Suggest a list of crops best suited for the specific location's climate, soil conditions, and elevation. Prioritize crops known for their sustainability and low environmental impact. Sustainable Growing Methods: Recommend sustainable practices based on the data, such as: Crop rotation strategies to improve soil health. Water conservation techniques like drip irrigation. Organic pest and disease management methods. Techniques to minimize soil erosion. Additional Considerations: If the data reveals any limitations (e.g., unsuitable soil pH), suggest appropriate amendments or alternative crops. Briefly explain the reasoning behind each recommendation, connecting it to the specific data points. Remember: Maintain a positive and encouraging tone. Emphasize the importance of sustainable practices for long-term success. Offer additional resources or suggest contacting local agricultural experts for further guidance."""
    print(messages)
    response = ollama.generate(model="qwen:1.8b", prompt=f"""Prompt : {system_prompt}\n\nContext:{messages}""", stream=False)
    
    print(response["response"])
    with open(f"outputs/{uid}/mindfulness.txt", "a") as f:
        session_response = f"""User : {messages_str}\n\nSage : {response["response"]}"""
        f.write(session_response)
                
    return jsonify(response["response"].replace("\n",""))    


@app.post("/chat")
def chat():
    messages_str = request.json.get("messages")
    uid = request.json.get("uid")
    previous_messages =""
    # create_medical_summary(uid)
    if not os.path.exists("outputs"):
        os.mkdir("outputs")
    if not os.path.exists(f"outputs/{uid}"):
        os.mkdir(f"outputs/{uid}")
    with open(f"outputs/{uid}/medical_summary.txt", "a+") as f:
        previous_messages = f.read()
    
    messages = f"Previous Chat : {previous_messages}\n\nCurrent Question : {messages_str}"
    system_prompt = """You are Sage, a sustainability-focused agricultural consultant. You possess a vast knowledge of sustainable farming practices and regional ecosystems. You prioritize data-driven analysis for informed decision-making. You excel at interpreting GIS data and translating it into actionable recommendations. Given a JSON file containing the following agricultural data: Location: Specific coordinates (latitude and longitude) Soil Properties: pH, nutrient levels (nitrogen, phosphorus, potassium), organic matter content Climate Data: Average temperature, rainfall patterns, sunlight hours Elevation: Height above sea level Sage should analyze the data and provide a comprehensive response including: Suitable Crop Recommendations: Suggest a list of crops best suited for the specific location's climate, soil conditions, and elevation. Prioritize crops known for their sustainability and low environmental impact. Sustainable Growing Methods: Recommend sustainable practices based on the data, such as: Crop rotation strategies to improve soil health. Water conservation techniques like drip irrigation. Organic pest and disease management methods. Techniques to minimize soil erosion. Additional Considerations: If the data reveals any limitations (e.g., unsuitable soil pH), suggest appropriate amendments or alternative crops. Briefly explain the reasoning behind each recommendation, connecting it to the specific data points. Remember: Maintain a positive and encouraging tone. Emphasize the importance of sustainable practices for long-term success. Offer additional resources or suggest contacting local agricultural experts for further guidance."""
    print(messages)
    response = ollama.generate(model="qwen:1.8b", prompt=f"""Prompt : {system_prompt}\n\nContext:{messages}""", stream=False)
    
    print(response["response"])
    with open(f"outputs/{uid}/mindfulness.txt", "a") as f:
        session_response = f"""User : {messages_str}\n\nSage : {response["response"]}"""
        f.write(session_response)
                
    return jsonify(response["response"].replace("\n","")) 



@app.get("/")
def home():
    return "Welcome to the Health AI API"

if __name__ == '__main__':
    app.run(debug=True, port=3000)
