import logging
import requests
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from collections import defaultdict
import time

# 🔐 API keys
TELEGRAM_BOT_TOKEN = "7737877253:AAFnVHIQmAkpYR_UNp1G64bs_A-bCvllL_Y"
GOOGLE_PLACES_API_KEY = "AIzaSyCbz2sFmdMH0ziSm8Agj9ofK9SAZFXa30Q"

# 🧠 Cache
cache = defaultdict(lambda: (0, []))
CACHE_TIMEOUT = 300  # seconds

# 🔧 Logging
logging.basicConfig(level=logging.INFO)

# 🏁 Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location_button = KeyboardButton(text="📍 Share Location", request_location=True)
    reply_markup = ReplyKeyboardMarkup([[location_button]], resize_keyboard=True)
    await update.message.reply_text("🌍 Welcome! Share your location or type a city name to explore nearby destinations and hotels.",
                                    reply_markup=reply_markup)

# 📍 Handle location
async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_location = update.message.location
    await process_location(update, user_location.latitude, user_location.longitude)

# ✏️ Handle typed city
async def city_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text
    geo_data = get_coordinates_from_city(city)
    if not geo_data:
        await update.message.reply_text("❌ Couldn't find the location for the city. Try another.")
        return
    lat, lng = geo_data
    await process_location(update, lat, lng)

# 📦 Main processing function (used for both location & city)
async def process_location(update: Update, lat, lng):
    lat = round(lat, 2)
    lng = round(lng, 2)
    lang_code = update.message.from_user.language_code or 'en'

    current_time = time.time()
    if current_time - cache[(lat, lng)][0] < CACHE_TIMEOUT:
        places_data = cache[(lat, lng)][1]
    else:
        places_data = get_places_nearby(lat, lng)
        if places_data:
            cache[(lat, lng)] = (current_time, places_data)

    if not places_data:
        await update.message.reply_text("⚠️ Sorry, I couldn't fetch any travel data.")
        return

    response_text = "🏞️ *Nearby Attractions & Hotels:*\n\n"
    for place in places_data[:5]:
        name = place.get('name')
        rating = place.get('rating', 'N/A')
        address = place.get('vicinity', 'Not available')
        price_level = '₹' * place.get('price_level', 0)
        stars = f"{rating} ⭐" if rating != 'N/A' else "Rating not available"
        response_text += f"🏨 *{name}*\n{stars}\n📍 {address}\n💰 Price: {price_level or 'Not listed'}\n\n"

    best_time = "Every time is best time for traveling ."
    response_text += f"🗓️ *Best Time to Visit:* {best_time}"

    if lang_code != 'en':
        response_text = translate_text(response_text, lang_code)

    await update.message.reply_text(response_text, parse_mode="Markdown")

# 📍 Get coordinates from city name
def get_coordinates_from_city(city_name):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": city_name,
        "key": GOOGLE_PLACES_API_KEY
    }
    try:
        response = requests.get(url, params=params)
        results = response.json().get("results")
        if results:
            location = results[0]["geometry"]["location"]
            return location["lat"], location["lng"]
    except Exception as e:
        print("Geocoding error:", e)
    return None

# 🌐 Google Places API
def get_places_nearby(lat, lng):
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": 5000,
        "type": "lodging|tourist_attraction",
        "key": GOOGLE_PLACES_API_KEY
    }
    try:
        response = requests.get(url, params=params)
        return response.json().get("results", [])
    except Exception as e:
        print("Places API error:", e)
        return None

# 🌐 Translate
def translate_text(text, target_lang):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "en",
            "tl": target_lang,
            "dt": "t",
            "q": text
        }
        res = requests.get(url, params=params)
        translated = ''.join([t[0] for t in res.json()[0]])
        return translated
    except Exception as e:
        print("Translation error:", e)
        return text

# 🚀 Launch
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), city_query_handler))

    print("🤖 Bot is live!")
    app.run_polling()

if __name__ == "__main__":
    main()
