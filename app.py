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
import spacy
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

logger.info("Starting Telegram bot...")

nlp = spacy.load("en_core_web_sm")

# Explicitly load .env
load_dotenv(dotenv_path=".env")

# Load Environment Variables
DB_URL = os.getenv("DATABASE_URL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logger.debug(f"TELEGRAM_TOKEN: {TELEGRAM_TOKEN}")
logger.debug(f"DATABASE_URL: {DB_URL}")
logger.debug(f"WEBHOOK_URL: {WEBHOOK_URL}")
logger.debug(f"PORT from env: {os.getenv('PORT')}")

if not DB_URL:
    raise ValueError("DATABASE_URL is not set! Check your .env file or environment variables.")

print(f"Using DATABASE_URL: {DB_URL}")  # Debugging

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
        SELECT movie_id, title, genres, overview, vote_average, "cast"
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
            "cast": row[5] if isinstance(row[5], list) else json.loads(row[5]) if row[5] else []
        }
        movies.append(movie)
    
    cur.close()
    conn.close()
    return movies

# Load Movies into Memory
movies_data = fetch_movies()
print(f"Loaded {len(movies_data)} movies from PostgreSQL")

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

        # Expanded movie-related queries
        #conversations.extend([
        #    "Can you recommend a movie?", f"You should watch {title}. It's a {genre} film with a rating of {rating}.",
        #    "Suggest a good movie.", f"You might like {title}, a highly rated {genre} film.",
        #    "What’s a great movie to watch?", f"I recommend {title}. It's a {genre} movie with a {rating} rating.",
        #    "Give me a movie suggestion.", f"Sure! Try {title}, a fantastic {genre} film.",
        #    "What is a popular movie right now?", f"{title} is trending! It's a {genre} movie with a rating of {rating}.",
        #    "I want to watch something interesting.", f"How about {title}? It's a {genre} film with a compelling story.",
        #    "Give me a critically acclaimed movie.", f"{title} has received great reviews and has a rating of {rating}.",
        #    "What movie should I watch tonight?", f"Try watching {title}, a top-rated {genre} film.",
        #    "Surprise me with a movie!", f"You might enjoy {title}, a highly rated {genre} movie."
        #])

        # Expanded queries about specific movies
        conversations.extend([
            f"Tell me about {title}.", f"{title} is a {genre} movie. Overview: {overview}",
            f"What’s {title} about?", f"{title} is a {genre} movie. Here's the synopsis: {overview}",
            f"Can you describe {title}?", f"{title} is a {genre} film with this storyline: {overview}",
            f"What makes {title} special?", f"{title} is a fan favorite, known for its {genre} story and a rating of {rating}.",
            f"Why is {title} famous?", f"{title} is well-known for its {genre} storyline and outstanding performances."
        ])

        # Expanded genre-related queries
        #conversations.extend([
        #    f"What genre is {title}?", f"{title} falls under the {genre} genre.",
        #    f"Is {title} an action movie?", f"{title} is a {genre} movie.",
        #    f"Does {title} have any comedy?", f"{title} is a {genre} film.",
        #    f"I like {genre} movies. Any suggestions?", f"You might like {title}, a great {genre} film!",
        #    f"What are some must-watch {genre} films?", f"{title} is one of the best {genre} movies!"
        #])

        # Expanded rating-based queries
        conversations.extend([
            f"Is {title} a good movie?", f"{title} has a rating of {rating}. Many viewers liked it!",
            f"Would you recommend {title}?", f"Yes! {title} has a rating of {rating} and is well-received.",
            f"What do people think about {title}?", f"{title} has a {rating} rating and is considered a {genre} classic.",
            f"Should I watch {title}?", f"If you enjoy {genre} movies, you'll probably like {title}. It has a {rating} rating."
        ])

        # Expanded actor-related queries
        #for actor in movie["cast"]:
        #    conversations.extend([
        #        f"Which movies feature {actor}?", f"{actor} stars in {title}.",
        #        f"Has {actor} been in any famous movies?", f"Yes! {actor} appeared in {title}, a popular {genre} film.",
        #        f"Tell me a movie with {actor}.", f"{actor} is in {title}, which is a {genre} movie.",
        #        f"Give me a list of {actor}’s movies.", f"{actor} starred in {title} and more films.",
        #        f"Is {actor} a good actor?", f"{actor} is well known for their performances in movies like {title}.",
        #        f"What is {actor} best known for?", f"{actor} is famous for starring in movies like {title}.",
        #        f"Who are some co-stars of {actor}?", f"In {title}, {actor} starred alongside {cast}.",
        #        f"Has {actor} worked in {genre} movies?", f"Yes, {actor} has appeared in {genre} movies like {title}.",
        #    ])

    return conversations

# Configure and Train Chatterbot
#chatbot = ChatBot("MovieBot", storage_adapter="chatterbot.storage.SQLStorageAdapter")
chatbot = ChatBot("MovieBot", storage_adapter="chatterbot.storage.SQLStorageAdapter",
                  logic_adapters=[
                      {
                          'import_path': 'chatterbot.logic.BestMatch',
                          'default_response': "I'm sorry, but I don't understand.",
                          'maximum_similarity_threshold': 0.90
                      }
                  ])
trainer = ListTrainer(chatbot)
trainer.train(generate_movie_conversations())
print("Chatbot training complete using PostgreSQL data!")

# Function to Fetch Movie Recommendations from PostgreSQL
def get_movie_recommendation(query):
    """Fetch a movie recommendation from PostgreSQL based on user query."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT title, overview, genres, vote_average, "cast"
        FROM movies_full
        WHERE title ILIKE %s
        LIMIT 1;
    """, (f"%{query}%",))
    
    result = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if result:
        title, overview, genres, rating, cast_json = result
        if isinstance(cast_json, str):
            cast_list = json.loads(cast_json)[:5]  # Parse JSON if it's a string
        elif isinstance(cast_json, list):
            cast_list = cast_json[:5]  # Already a list, just slice it
        else:
            cast_list = []  # Handle unexpected cases gracefully
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


# Run the Bot in Async Mode
#if __name__ == "__main__":
#    nest_asyncio.apply()
#    asyncio.create_task(main())

import nest_asyncio
import asyncio

nest_asyncio.apply()  # Apply this to fix issues with nested event loops

async def main():
    """Starts the Telegram bot with Webhook"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🎬 MovieBot is running on Telegram with Webhook...")

    logger.info(f"Setting Telegram webhook to {WEBHOOK_URL}/{TELEGRAM_TOKEN}")

    await app.bot.setWebhook(f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}")
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 443)),  # Uses PORT env variable, defaults to 8443 if not set
        url_path=f"/{TELEGRAM_TOKEN}"
    )

if __name__ == "__main__":
    asyncio.run(main())

