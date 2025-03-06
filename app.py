import os
import json
import psycopg2
import nest_asyncio
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer

# Load environment variables
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Database Connection Function
def get_db_connection():
    """Establishes a PostgreSQL connection."""
    return psycopg2.connect(DB_URL)

# Fetch Movies from PostgreSQL
def fetch_movies():
    """Fetch movies from PostgreSQL and return a list of dicts."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT movie_id, title, genres, overview, vote_average, cast
        FROM movies_full;
    """)
    
    movies = []
    for row in cur.fetchall():
        movie = {
            "id": row[0],
            "title": row[1],
            "genres": row[2],
            "overview": row[3],
            "vote_average": row[4],
            "cast": json.loads(row[5]) if row[5] else []
        }
        movies.append(movie)
    
    cur.close()
    conn.close()
    return movies

# Load Movies into Memory
movies_data = fetch_movies()
print(f"✅ Loaded {len(movies_data)} movies from PostgreSQL")

# Generate Conversations for Chatterbot Training
def generate_movie_conversations():
    """Formats movie data for Chatterbot training."""
    conversations = []
    
    for movie in movies_data:
        title = movie["title"]
        genre = movie["genres"]
        overview = movie["overview"]
        rating = movie["vote_average"]
        cast = ", ".join(movie["cast"]) if movie["cast"] else "unknown actors"

        conversations.extend([
            f"Tell me about {title}.", f"{title} is a {genre} movie. Overview: {overview}",
            f"Would you recommend {title}?", f"Yes! {title} has a rating of {rating} and is well-received.",
            f"Who stars in {title}?", f"{title} features {cast}.",
            f"What genre is {title}?", f"{title} falls under the {genre} genre.",
            f"Should I watch {title}?", f"If you enjoy {genre} movies, you'll like {title} (Rating: {rating})."
        ])

    return conversations

# Configure and Train Chatterbot
chatbot = ChatBot("MovieBot", storage_adapter="chatterbot.storage.SQLStorageAdapter")
trainer = ListTrainer(chatbot)
trainer.train(generate_movie_conversations())
print("✅ Chatbot training complete using PostgreSQL data!")

# Function to Fetch Movie Recommendations from PostgreSQL
def get_movie_recommendation(query):
    """Fetch a movie recommendation from PostgreSQL based on user query."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT title, overview, genres, vote_average, cast
        FROM movies_full
        WHERE title ILIKE %s
        LIMIT 1;
    """, (f"%{query}%",))
    
    result = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if result:
        title, overview, genres, rating, cast_json = result
        cast_list = json.loads(cast_json)[:5]  # Get top 5 cast members
        cast_names = ", ".join(cast_list)
        return f"🎬 {title}\n📖 {overview}\n⭐ Genre: {genres}\n💯 Rating: {rating}\n🎭 Cast: {cast_names}"
    else:
        return "I couldn't find that movie in my database."

# Telegram Bot Handlers
async def start(update: Update, context: CallbackContext):
    """Handles /start command"""
    await update.message.reply_text("Hello! Ask me about movies, actors, or recommendations.")

async def handle_message(update: Update, context: CallbackContext):
    """Handles user messages and queries Chatterbot & PostgreSQL"""
    user_text = update.message.text

    # Query PostgreSQL for movie recommendations
    response = get_movie_recommendation(user_text)
    
    # If no recommendation found, fall back to Chatterbot response
    if response == "I couldn't find that movie in my database.":
        response = chatbot.get_response(user_text)

    await update.message.reply_text(str(response))

# Telegram Bot Initialization
async def main():
    """Starts the Telegram bot with async handling"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🎬 MovieBot is running on Telegram...")
    await app.run_polling()

# Run the Bot in Async Mode
if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.create_task(main())
