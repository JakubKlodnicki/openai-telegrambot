import os
from openai import OpenAI
import asyncio
from dotenv import load_dotenv, find_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from PyPDF2 import PdfReader
import pandas as pd
import pytesseract
from PIL import Image

BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)
load_dotenv(find_dotenv())
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MAIN_STATE = range(1)

# Lista dozwolonych użytkowników (ID użytkowników)
ALLOWED_USERS = {6639144618}  # Przykładowe ID użytkowników

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    if user_id in ALLOWED_USERS:
        await update.message.reply_text(
        "Dostępne komendy:\n"
        "/start - Rozpocznij konwersację i zaloguj się\n"
        "/gpt3 - Wybierz model GPT-3.5\n"
        "/gpt4 - Wybierz model GPT-4\n"
        "/gpt4o - Wybierz model GPT-4o\n"
        "/dalle - Wybierz DALL-E\n"
        "/generate_image - Generuj obraz na podstawie opisu\n"
        "/help - Wyświetl listę dostępnych komend\n"
    )
        return MAIN_STATE
    else:
        await update.message.reply_text('Nie masz uprawnień do korzystania z tego bota.')
        return ConversationHandler.END

async def choose_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id in ALLOWED_USERS:
        if update.message.text.lower() == '/gpt3':
            context.user_data['gpt_version'] = 'gpt-3.5-turbo'
            context.user_data['chat_history'] = []  # Reset history for new session
            await update.message.reply_text('Wybrano GPT-3.5. Możesz zadawać pytania.')
        elif update.message.text.lower() == '/gpt4':
            context.user_data['gpt_version'] = 'gpt-4'
            context.user_data['chat_history'] = []  # Reset history for new session
            await update.message.reply_text('Wybrano GPT-4. Możesz zadawać pytania.')
        elif update.message.text.lower() == '/gpt4o':
            context.user_data['gpt_version'] = 'gpt-4o'
            context.user_data['chat_history'] = []  # Reset history for new session
            await update.message.reply_text('Wybrano GPT-4o. Możesz zadawać pytania.')
        elif update.message.text.lower() == '/dalle':
            context.user_data['gpt_version'] = 'dall-e'
            context.user_data['chat_history'] = []  # Reset history for new session
            await update.message.reply_text('Wybrano DALL-E. Możesz zadawać pytania.')

async def chatgpt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id in ALLOWED_USERS:
        model = context.user_data.get('gpt_version')
        if not model:
            await update.message.reply_text('Nie wybrano modelu. Wybierz wersję GPT: /gpt3, /gpt4, /gpt4o bądź DALLE')
            return
        prompt = update.message.text

        # Retrieve the chat history and file analysis
        chat_history = context.user_data.get('chat_history', [])
        file_analysis = context.user_data.get('file_analysis', '')

        if file_analysis:
            chat_history.append({"role": "user", "content": f"Analiza pliku:\n\n{file_analysis}"})

        chat_history.append({"role": "user", "content": prompt})

        try:
            response = client.chat.completions.create(
                model=model,
                messages=chat_history
            )
            reply = response.choices[0].message.content
            chat_history.append({"role": "assistant", "content": reply})
            context.user_data['chat_history'] = chat_history

            await update.message.reply_text(reply)
        except Exception as e:
            await update.message.reply_text(f'Wystąpił błąd: {str(e)}')
    else:
        await update.message.reply_text('Nie masz uprawnień do korzystania z tego bota.')

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id in ALLOWED_USERS:
        prompt = update.message.text.split('/generate_image', 1)[-1].strip()
        if not prompt:
            await update.message.reply_text('Podaj opis obrazu po komendzie /generate_image.')
            return
        try:
            response = client.images.generate(prompt=prompt, n=1, size="1024x1024")
            image_url = response['data'][0]['url']
            await update.message.reply_photo(photo=image_url)
        except Exception as e:
            await update.message.reply_text(f'Wystąpił błąd: {str(e)}')
    else:
        await update.message.reply_text('Nie masz uprawnień do korzystania z tego bota.')

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id in ALLOWED_USERS:
        file = update.message.document
        file_id = file.file_id
        retries = 3
        for attempt in range(retries):
            try:
                new_file = await context.bot.get_file(file_id)
                file_path = f"downloads/{file.file_name}"
                await new_file.download_to_drive(file_path)
                await update.message.reply_text(f'Plik zapisany: {file_path}')
                break
            except Exception as e:
                if attempt < retries - 1:
                    await update.message.reply_text('Wystąpił błąd przy pobieraniu pliku, ponawiam próbę...')
                    await asyncio.sleep(2)
                else:
                    await update.message.reply_text(f'Wystąpił błąd przy pobieraniu pliku: {str(e)}')
                    return

        model = context.user_data.get('gpt_version')
        if model not in ['gpt-4', 'gpt-4o']:
            await update.message.reply_text('Wybrany model nie obsługuje analizy plików.')
            return

        try:
            if file.file_name.endswith('.pdf'):
                text = extract_text_from_pdf(file_path)
            elif file.file_name.endswith('.csv'):
                text = extract_text_from_csv(file_path)
            elif file.file_name.endswith(('.py', '.txt', '.js', '.html', '.css', '.json', '.xml', '.sql', '.md', '.c', '.cpp', '.java', '.rb', '.php', '.sh', '.bat', '.ini', '.yml', '.yaml', '.r', '.pl')):
                text = extract_text_from_text_file(file_path)
            elif file.file_name.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                text = extract_text_from_image(file_path)
            else:
                await update.message.reply_text('Nieobsługiwany format pliku.')
                return

            if text.strip():
                context.user_data['file_analysis'] = text

                # Add the file analysis to the chat history
                chat_history = context.user_data.get('chat_history', [])
                chat_history.append({"role": "user", "content": f"Proszę przeanalizować następujący tekst z pliku:\n\n{text}"})
                context.user_data['chat_history'] = chat_history

                response = client.chat.completions.create(
                    model=model,
                    messages=chat_history
                )
                reply = response.choices[0].message.content
                chat_history.append({"role": "assistant", "content": reply})
                context.user_data['chat_history'] = chat_history

                await update.message.reply_text(reply)
            else:
                await update.message.reply_text(f'Niestety, nie udało się rozpoznać tekstu na obrazie. Tekst OCR: {text}')
        except Exception as e:
            await update.message.reply_text(f'Wystąpił błąd podczas analizy pliku: {str(e)}')
    else:
        await update.message.reply_text('Nie masz uprawnień do korzystania z tego bota.')

def extract_text_from_image(image_path):
    try:
        text = pytesseract.image_to_string(Image.open(image_path))
        return text
    except Exception as e:
        return f'Błąd podczas rozpoznawania tekstu: {str(e)}'


def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_csv(csv_path):
    df = pd.read_csv(csv_path)
    return df.to_string()

def extract_text_from_text_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id in ALLOWED_USERS:
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        file_path = f"downloads/{photo_file.file_id}.jpg"
        await photo_file.download_to_drive(file_path)
        await update.message.reply_text(f'Obraz zapisany: {file_path}')

        try:
            text = extract_text_from_image(file_path)
            if text.strip():
                await update.message.reply_text(f'Rozpoznany tekst:\n\n{text}')
            else:
                await update.message.reply_text(f'Niestety, nie udało się rozpoznać tekstu na obrazie. Tekst OCR: {text}')
        except Exception as e:
            await update.message.reply_text(f'Wystąpił błąd podczas analizy obrazu: {str(e)}')
    else:
        await update.message.reply_text('Nie masz uprawnień do korzystania z tego bota.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Dostępne komendy:\n"
        "/start - Rozpocznij konwersację i zaloguj się\n"
        "/gpt3 - Wybierz model GPT-3.5\n"
        "/gpt4 - Wybierz model GPT-4\n"
        "/gpt4o - Wybierz model GPT-4o\n"
        "/dalle - Wybierz DALL-E\n"
        "/generate_image - Generuj obraz na podstawie opisu\n"
        "/help - Wyświetl listę dostępnych komend\n"
    )
    await update.message.reply_text(help_text)

def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_STATE: [
                CommandHandler('gpt3', choose_gpt),
                CommandHandler('gpt4', choose_gpt),
                CommandHandler('gpt4o', choose_gpt),
                CommandHandler('dalle', choose_gpt),
                MessageHandler(filters.TEXT & ~filters.COMMAND, chatgpt),
            ],
        },
        fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('generate_image', generate_image))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))

    application.run_polling()

if __name__ == '__main__':
    os.makedirs('downloads', exist_ok=True)
    main()
