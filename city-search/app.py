import os
from flask import Flask, request, jsonify, render_template
import requests
from pymongo import MongoClient, errors
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='templates')

# Environment variables
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
MONGODB_HOST = os.getenv('MONGODB_HOST', 'mongodb-service')

# Connect to MongoDB (Optional for caching)
try:
    client = MongoClient(MONGODB_HOST, 27017, serverSelectionTimeoutMS=5000)
    db = client['city_search_cache']
    cache_collection = db['weather_cache']
    app.logger.info('Connected to MongoDB for caching.')
except errors.ServerSelectionTimeoutError as err:
    app.logger.error(f'Error connecting to MongoDB: {err}')
    client = None

@app.route('/', methods=['GET'])
def index():
    return render_template('search.html')

@app.route('/search', methods=['POST'])
def search():
    try:
        city = request.form.get('city')
        if not city:
            return jsonify({'error': 'Please provide a city name.'}), 400

        city = city.strip()

        # Check cache (if MongoDB is connected)
        weather_data = None
        if client:
            cache_entry = cache_collection.find_one({'city': city.lower(), 'timestamp': {'$gte': datetime.utcnow() - timedelta(minutes=30)}})
            if cache_entry:
                weather_data = cache_entry['data']
                app.logger.info(f'Retrieved weather data for {city} from cache.')

        # If not in cache, fetch from API
        if not weather_data:
            # Fetch data from WeatherAPI
            response = requests.get('http://api.weatherapi.com/v1/current.json',
                                    params={'key': WEATHER_API_KEY, 'q': city})
            data = response.json()

            if 'error' in data:
                error_message = data['error']['message']
                app.logger.error(f"Error fetching data for {city}: {error_message}")
                return jsonify({'error': error_message}), 400

            weather_data = data

            # Store in cache
            if client:
                cache_collection.update_one(
                    {'city': city.lower()},
                    {'$set': {'data': weather_data, 'timestamp': datetime.utcnow()}},
                    upsert=True
                )
                app.logger.info(f'Stored weather data for {city} in cache.')

        # Render the result
        return jsonify(weather_data), 200

    except Exception as e:
        app.logger.error(f"Exception in search: {e}")
        return render_template('search.html', error='An error occurred while processing your request.')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)