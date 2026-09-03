from flask import Flask, render_template, request, redirect
import os
import requests
import sqlite3
from dotenv import load_dotenv
from datetime import datetime

# Load API key from .env file
load_dotenv()

# Create Flask application
app = Flask(__name__)

# Get API key
API_KEY = os.getenv("WEATHER_API_KEY")


# Create SQLite database and search history table
def init_db():
    connection = sqlite3.connect("weather.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            searched_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


init_db()


@app.route("/", methods=["GET", "POST"])
def home():
    weather = None
    forecast = None
    error = None

    if request.method == "POST":
        city = request.form.get("city")
    else:
        city = request.args.get("city")

    if city:
        city = city.strip()

        current_weather_url = (
            "https://api.openweathermap.org/data/2.5/weather"
        )

        forecast_url = (
            "https://api.openweathermap.org/data/2.5/forecast"
        )

        parameters = {
            "q": city,
            "appid": API_KEY,
            "units": "metric"
        }

        try:
            # Get current weather
            response = requests.get(
                current_weather_url,
                params=parameters,
                timeout=10
            )

            data = response.json()

            if response.status_code == 200:
                weather = data

                # Convert sunrise and sunset timestamps
                weather["formatted_sunrise"] = datetime.fromtimestamp(
                    weather["sys"]["sunrise"]
                ).strftime("%I:%M %p")

                weather["formatted_sunset"] = datetime.fromtimestamp(
                    weather["sys"]["sunset"]
                ).strftime("%I:%M %p")

                # Get 5-day forecast
                forecast_response = requests.get(
                    forecast_url,
                    params=parameters,
                    timeout=10
                )

                forecast_data = forecast_response.json()

                if forecast_response.status_code == 200:
                    forecast = []

                    for item in forecast_data["list"][::8]:

                        date = datetime.strptime(
                            item["dt_txt"],
                            "%Y-%m-%d %H:%M:%S"
                        )

                        item["formatted_date"] = date.strftime(
                            "%A, %b %d"
                        )

                        forecast.append(item)

                else:
                    error = forecast_data.get(
                        "message",
                        "Could not get forecast data"
                    )

                # Save valid searches without duplicates
                if request.method == "POST" and not error:

                    connection = sqlite3.connect("weather.db")
                    cursor = connection.cursor()

                    city_name = weather["name"]

                    cursor.execute(
                        "DELETE FROM search_history WHERE city = ?",
                        (city_name,)
                    )

                    cursor.execute(
                        """
                        INSERT INTO search_history
                        (city, searched_at)
                        VALUES (?, ?)
                        """,
                        (
                            city_name,
                            datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        )
                    )

                    connection.commit()
                    connection.close()

            else:
                error = data.get(
                    "message",
                    "Something went wrong"
                )

        except requests.RequestException:
            error = "Unable to connect to the weather service."

    # Get recent searches
    connection = sqlite3.connect("weather.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT city, searched_at
        FROM search_history
        ORDER BY id DESC
        LIMIT 5
    """)

    search_history = cursor.fetchall()
    connection.close()

    return render_template(
        "index.html",
        weather=weather,
        forecast=forecast,
        error=error,
        search_history=search_history
    )


# Clear all search history
@app.route("/clear-history", methods=["POST"])
def clear_history():

    connection = sqlite3.connect("weather.db")
    cursor = connection.cursor()

    cursor.execute("DELETE FROM search_history")

    connection.commit()
    connection.close()

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)