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

def get_details_from_user_pdf(user_id):
    if not os.path.exists("outputs"):
        return jsonify({"message": "No files found"})

    os.chdir("outputs")

    if not os.path.exists(user_id):
        return jsonify({"message": "No files found"})

    os.chdir(user_id)

    text_path_urls = []

    for folder_name in os.listdir():
        folder_path = os.path.join(os.getcwd(), folder_name)
        if os.path.isdir(folder_path):
            for page_folder in os.listdir(folder_path):
                page_folder_path = os.path.join(folder_path, page_folder)
                if os.path.isdir(page_folder_path):
                    for file_name in os.listdir(page_folder_path):
                        if file_name.endswith(".txt"):
                            file_path = os.path.join(page_folder_path, file_name)
                            newfilepath = file_path.replace(f"{BASEURL}/outputs/{user_id}/", "")
                            print(newfilepath)
                            text_path_urls.append(newfilepath)

    return text_path_urls



app = Flask(__name__)
client = anthropic.Client(api_key=API_KEY)
app.config['SECRET_KEY'] = 'secret!'



@app.post("/crop-detail")
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
    system_prompt = """You are Terra, a sustainability-focused agricultural consultant. You possess a vast knowledge of sustainable farming practices and regional ecosystems. You prioritize data-driven analysis for informed decision-making. You excel at interpreting GIS data and translating it into actionable recommendations. Given a JSON file containing the following agricultural data: Location: Specific coordinates (latitude and longitude) Soil Properties: pH, nutrient levels (nitrogen, phosphorus, potassium), organic matter content Climate Data: Average temperature, rainfall patterns, sunlight hours Elevation: Height above sea level Terra should analyze the data and provide a comprehensive response including: Suitable Crop Recommendations: Suggest a list of crops best suited for the specific location's climate, soil conditions, and elevation. Prioritize crops known for their sustainability and low environmental impact. Sustainable Growing Methods: Recommend sustainable practices based on the data, such as: Crop rotation strategies to improve soil health. Water conservation techniques like drip irrigation. Organic pest and disease management methods. Techniques to minimize soil erosion. Additional Considerations: If the data reveals any limitations (e.g., unsuitable soil pH), suggest appropriate amendments or alternative crops. Briefly explain the reasoning behind each recommendation, connecting it to the specific data points. Remember: Maintain a positive and encouraging tone. Emphasize the importance of sustainable practices for long-term success. Offer additional resources or suggest contacting local agricultural experts for further guidance."""
    print(messages)
    response = ollama.generate(model="qwen:1.8b", prompt=f"""Prompt : {system_prompt}\n\nContext:{messages}""", stream=False)
    
    print(response["response"])
    with open(f"outputs/{uid}/mindfulness.txt", "a") as f:
        session_response = f"""User : {messages_str}\n\nSage : {response["response"]}"""
        f.write(session_response)
                
    return jsonify(response["response"].replace("\n",""))    



@app.post("/sos")
def sos():
    uid = request.json.get("uid")
    source = request.json.get("source")
    location = request.json.get("location")
    target = request.json.get("target")
    
    print(uid, source, location, target)
    
    return jsonify({"message": "success"})


@app.get("/")
def home():
    return "Welcome to the Health AI API"

if __name__ == '__main__':
    app.run(debug=True)
