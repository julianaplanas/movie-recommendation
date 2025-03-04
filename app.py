import pandas as pd
import ast
import os
import nest_asyncio
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from chatterbot import ChatBot
from chatterbot.trainers import ListTrainer
import subprocess

DATA_PATH = "data"
CREDITS_FILE = f"{DATA_PATH}/credits.csv"
MOVIES_FILE = f"{DATA_PATH}/movies_metadata.csv"

def download_data():
    """Downloads the dataset only if it doesn't exist."""
    data_dir = "data"
    movies_path = os.path.join(data_dir, "movies_metadata.csv")
    credits_path = os.path.join(data_dir, "credits.csv")

    # Create data directory if not exists
    os.makedirs(data_dir, exist_ok=True)

    # Check if files already exist
    if os.path.exists(movies_path) and os.path.exists(credits_path):
        print("Dataset is ready. Skipping download.")
        return  # Exit function if files exist

    print("Downloading dataset...")

    # Download movies_metadata.csv
    if not os.path.exists(movies_path):
        os.system(f"wget -O {movies_path} 'https://drive.google.com/file/d/1IJYO07SDczRHZNJ3jRbz3A_VhFRCpzL3'")

    # Download credits.csv
    if not os.path.exists(credits_path):
        os.system(f"wget -O {credits_path} 'https://drive.google.com/file/d/1Qma0SUoQ56ZthSuaZtw5tORZ0nEOStS-'")

    print("Download completed!")

# Run the function at startup
download_data()

movies_df = pd.read_csv(MOVIES_FILE, sep=None, engine="python")
credits_df = pd.read_csv(CREDITS_FILE, sep=None, engine="python")

print(movies_df.head())
print(movies_df.columns)
print(credits_df.head())
print(credits_df.columns)

print("Movie dataset loaded successfully!")

# Preprocess Movies Data
movies_df = movies_df[["id", "title", "genres", "overview", "vote_average"]]
movies_df["id"] = pd.to_numeric(movies_df["id"], errors="coerce")
movies_df = movies_df.dropna(subset=["id"]).astype({"id": "int"})
movies_df["genres"] = movies_df["genres"].apply(lambda x: [genre["name"] for genre in ast.literal_eval(x)] if isinstance(x, str) else [])

# Preprocess Credits Data
credits_df = credits_df[["id", "cast"]]
credits_df["id"] = pd.to_numeric(credits_df["id"], errors="coerce")
credits_df = credits_df.dropna(subset=["id"]).astype({"id": "int"})

def extract_actors(cast_str):
    try:
        cast_list = ast.literal_eval(cast_str)
        return [actor["name"] for actor in cast_list]
    except (ValueError, SyntaxError):
        return []

credits_df["cast"] = credits_df["cast"].apply(extract_actors)

# Merge Datasets
merged_df = movies_df.merge(credits_df, on="id", how="inner")

# Generate Conversations
def generate_movie_conversations():
    """Formats movie data for Chatterbot."""
    conversations = []
    for _, row in merged_df.iterrows():
        title = row["title"]
        genre = ", ".join(row["genres"])
        overview = row["overview"]
        rating = row["vote_average"]
        cast = ", ".join(row["cast"]) if row["cast"] else "unknown actors"

        # Expanded movie-related queries
        conversations.extend([
            "Can you recommend a movie?", f"You should watch {title}. It's a {genre} film with a rating of {rating}.",
            "Suggest a good movie.", f"You might like {title}, a highly rated {genre} film.",
            "What’s a great movie to watch?", f"I recommend {title}. It's a {genre} movie with a {rating} rating.",
            "Give me a movie suggestion.", f"Sure! Try {title}, a fantastic {genre} film.",
            "What is a popular movie right now?", f"{title} is trending! It's a {genre} movie with a rating of {rating}.",
            "I want to watch something interesting.", f"How about {title}? It's a {genre} film with a compelling story.",
            "Give me a critically acclaimed movie.", f"{title} has received great reviews and has a rating of {rating}.",
            "What movie should I watch tonight?", f"Try watching {title}, a top-rated {genre} film.",
            "Surprise me with a movie!", f"You might enjoy {title}, a highly rated {genre} movie."
        ])

        # Expanded queries about specific movies
        conversations.extend([
            f"Tell me about {title}.", f"{title} is a {genre} movie. Overview: {overview}",
            f"What’s {title} about?", f"{title} is a {genre} movie. Here's the synopsis: {overview}",
            f"Can you describe {title}?", f"{title} is a {genre} film with this storyline: {overview}",
            f"What makes {title} special?", f"{title} is a fan favorite, known for its {genre} story and a rating of {rating}.",
            f"Why is {title} famous?", f"{title} is well-known for its {genre} storyline and outstanding performances."
        ])

        # Expanded genre-related queries
        conversations.extend([
            f"What genre is {title}?", f"{title} falls under the {genre} genre.",
            f"Is {title} an action movie?", f"{title} is a {genre} movie.",
            f"Does {title} have any comedy?", f"{title} is a {genre} film.",
            f"I like {genre} movies. Any suggestions?", f"You might like {title}, a great {genre} film!",
            f"What are some must-watch {genre} films?", f"{title} is one of the best {genre} movies!"
        ])

        # Expanded rating-based queries
        conversations.extend([
            f"Is {title} a good movie?", f"{title} has a rating of {rating}. Many viewers liked it!",
            f"Would you recommend {title}?", f"Yes! {title} has a rating of {rating} and is well-received.",
            f"What do people think about {title}?", f"{title} has a {rating} rating and is considered a {genre} classic.",
            f"Should I watch {title}?", f"If you enjoy {genre} movies, you'll probably like {title}. It has a {rating} rating."
        ])

        # Expanded actor-related queries
        for actor in row["cast"]:
            conversations.extend([
                f"Which movies feature {actor}?", f"{actor} stars in {title}.",
                f"Has {actor} been in any famous movies?", f"Yes! {actor} appeared in {title}, a popular {genre} film.",
                f"Tell me a movie with {actor}.", f"{actor} is in {title}, which is a {genre} movie.",
                f"Give me a list of {actor}’s movies.", f"{actor} starred in {title} and more films.",
                f"Is {actor} a good actor?", f"{actor} is well known for their performances in movies like {title}.",
                f"What is {actor} best known for?", f"{actor} is famous for starring in movies like {title}.",
                f"Who are some co-stars of {actor}?", f"In {title}, {actor} starred alongside {cast}.",
                f"Has {actor} worked in {genre} movies?", f"Yes, {actor} has appeared in {genre} movies like {title}.",
            ])

    return conversations

# Train Chatterbot
chatbot = ChatBot("MovieBot", storage_adapter="chatterbot.storage.SQLStorageAdapter")
trainer = ListTrainer(chatbot)
trainer.train(generate_movie_conversations())
print("Chatbot training complete!")

# Load Telegram Token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Telegram Bot Handlers
async def start(update: Update, context: CallbackContext):
    """Handles /start command"""
    await update.message.reply_text("Hello! Ask me about movies, actors, or recommendations.")

async def handle_message(update: Update, context: CallbackContext):
    """Handles user messages and queries Chatterbot"""
    user_text = update.message.text
    response = chatbot.get_response(user_text)
    await update.message.reply_text(str(response))

async def main():
    """Starts the Telegram bot with async handling"""
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("MovieBot is running on Telegram...")
    await app.run_polling()

# Run the Bot in Async Mode
if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.create_task(main())
