import os
from pymongo import MongoClient
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
MONGODB_HOST = os.getenv('MONGODB_HOST', 'mongodb-service')

# MongoDB connection
client = MongoClient(MONGODB_HOST, 27017)
db = client['weather_data']

# List of major cities
CITIES = ['London', 'New York', 'Tokyo', 'Paris', 'Sydney']

def fetch_and_store_weather_data():
    for city in CITIES:
        try:
            # Fetch data from WeatherAPI
            response = requests.get('http://api.weatherapi.com/v1/current.json',
                                    params={'key': WEATHER_API_KEY, 'q': city})
            data = response.json()

            if 'error' in data:
                logger.error(f"Error fetching data for {city}: {data['error']['message']}")
                continue

            # Store data in MongoDB, using city name as collection name
            collection_name = city.lower().replace(' ', '_')
            collection = db[collection_name]
            collection.insert_one(data)

            logger.info(f"Successfully stored data for {city}")

        except Exception as e:
            logger.error(f"Exception fetching data for {city}: {e}")

if __name__ == '__main__':
    fetch_and_store_weather_data()