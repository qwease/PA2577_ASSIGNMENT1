import os
from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
import requests

app = Flask(__name__, template_folder='templates')


# Environment variables
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
IP_API_KEY = os.getenv('IP_API_KEY')  # If using a service like ipgeolocation.io
MONGODB_HOST = os.getenv('MONGODB_HOST', 'mongodb-service')
CITY_SEARCH_SERVICE_URL = os.getenv('CITY_SEARCH_SERVICE_URL', 'http://city-search-service:5000')

# MongoDB connection
client = MongoClient(MONGODB_HOST, 27017)
db = client['user_data']
ip_collection = db['ip_data']

# Database for major cities
weather_db = client['weather_data']
CITIES = ['London', 'New York', 'Tokyo', 'Paris', 'Sydney']

@app.route('/submit-ip', methods=['POST'])
def submit_ip():
    try:
        data = request.get_json()
        user_ip = data.get('ip')
        app.logger.info(f"User IP from client: {user_ip}")

        weather_data = get_weather_data(user_ip)

        if not weather_data:
            return jsonify({'error': 'Unable to fetch weather data for your IP.'}), 500

        # Store IP address and weather data in MongoDB
        ip_collection.insert_one({
            'ip': user_ip,
            'weather_data': weather_data
        })

        # Render weather information as HTML
        weather_html = render_template('weather.html', weather=weather_data, ip=user_ip)
        app.logger.info(weather_html)
        return jsonify({'weather_html': weather_html}), 200
    except Exception as e:
        app.logger.error(f"Exception in submit_ip: {e}")
        return jsonify({'error': 'An error occurred.'}), 500
    
@app.route('/', methods=['GET'])
def index():
    try:
        return render_template('index.html', major_cities_weather=get_major_city_weather())
    except Exception as e:
        app.logger.error(f"Exception in index: {e}")
        return "An error occurred.", 500

@app.route('/status', methods=['GET'])
def status():
    system_usage = get_system_usage()
    if system_usage['status'] == 'running':
        return render_template('status.html', status=system_usage['status'],System=system_usage['System'], CPU_Usage=system_usage['CPU_Usage'],Memory_Usage=system_usage['Memory_Usage'])
    return render_template('status.html', status=system_usage['status'], error=system_usage['error'])

@app.route('/search', methods=['POST'])
def search_city():
    city = request.form.get('city')
    if not city:
        error_message = "Please enter a city name."
        return render_template('index.html', error_message=error_message)

    # Communicate with the City Search Microservice
    try:
        # Send the search request to the city search service
        response = requests.post(f'{CITY_SEARCH_SERVICE_URL}/search', data={'city': city}, timeout=5)
        major_cities_weather=get_major_city_weather()
        
        # Parse the weather data from the city search service
        weather_data = response.json()
        if response.status_code == 200:
            
            # Render the index.html template with the searched_weather context
            return render_template('index.html', searched_weather=weather_data, major_cities_weather=major_cities_weather)
        else:
            # Handle errors returned by the city search service
            app.logger.info(weather_data)
            error_message = weather_data['error']
            return render_template('index.html', error_message=error_message, major_cities_weather=major_cities_weather)
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error communicating with City Search Service: {e}")
        error_message = "Unable to contact the City Search Service."
        return render_template('index.html', error_message=error_message, major_cities_weather=major_cities_weather)

def get_major_city_weather():
    # Fetch major city weather data from MongoDB
    major_cities_weather = []
    for city in CITIES:
        collection_name = city.lower().replace(' ', '_')
        collection = weather_db[collection_name]
        # Get the most recent weather data
        city_weather_data = collection.find_one(sort=[('_id', -1)])
        if city_weather_data:
            major_cities_weather.append(city_weather_data)
        else:
            app.logger.warning(f"No weather data found for {city} in MongoDB.")
    return major_cities_weather

def get_system_usage():
    import psutil
    import platform

    try:
        # Get platform info
        system = platform.system()
        
        # CPU usage (per-cpu=False gets the overall CPU percentage)
        cpu_percent = psutil.cpu_percent(interval=1, percpu=False)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        app.logger.info({
            'status': 'running',
            'System': str(system),
            'CPU_Usage': f'{cpu_percent}%',
            'Memory_Usage': f'{memory_percent}%'
            })
        return {
            'status': 'running',
            'System': str(system),
            'CPU_Usage': f'{cpu_percent}%',
            'Memory_Usage': f'{memory_percent}%'
            }
    except psutil.Error as e:
        return {
            'status': 'error',
            'error': f"Error getting system stats: {e}"
            }
    except Exception as e:
        return {
            'status': 'error',
            'error': f"Unexpected error: {e}"
            }

def get_weather_data(query):
    try:
        response = requests.get('http://api.weatherapi.com/v1/current.json',
                                params={'key': WEATHER_API_KEY, 'q': query})
        data = response.json()
        app.logger.info(f'http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={query}&api=yes')
        if 'error' in data:
            app.logger.error(f"Error fetching weather data: {data['error']['message']}")
            return None

        return data
    except Exception as e:
        app.logger.error(f"Exception in get_weather_data: {e}")
        return None
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)