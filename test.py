import logging
import requests
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext
import os
import re
import time

# Replace with your own bot token
TELEGRAM_TOKEN = '7509017987:AAEfiGeSmNViCdT32sG1wPCX7b10fNxH6mQ'

# Channel to force join
FORCE_JOIN_CHANNEL = 'https://t.me/AnotherHappyboy'

# Developer details
DEVELOPER = "Reckless"
DEVELOPER_USERNAME = "@recklessevader"

# TeraBox mirror URLs
TERABOX_URLS = [
    "mirrobox.com", "nephobox.com", "freeterabox.com", "1024tera.com",
    "4funbox.co", "terabox.app", "terabox.fun", "momerybox.com",
    "tibibox.com", "terabox.com"
]

# Function to call the first API for file info
def get_terabox_info(file_id, password=''):
    api_url = f"https://terabox.hnn.workers.dev/api/get-info?shorturl={file_id}&pwd={password}"
    response = requests.get(api_url)
    if response.status_code != 200:
        return None
    return response.json()

# Function to get the download link
def get_download_link(file_id, password=''):
    try:
        info = get_terabox_info(file_id, password)
        if not info or 'list' not in info or not info['list']:
            return "Error: Unable to retrieve file information."

        file_data = info['list'][0]
        post_data = {
            'shareid': info['shareid'],
            'uk': info['uk'],
            'sign': info['sign'],
            'timestamp': info['timestamp'],
            'fs_id': file_data['fs_id']
        }

        download_api_url = "https://terabox.hnn.workers.dev/api/get-download"
        headers = {
            'Accept': '*/*',
            'Content-Type': 'application/json',
        }

        response = requests.post(download_api_url, json=post_data, headers=headers)
        response.raise_for_status()

        download_info = response.json()
        if 'downloadLink' in download_info:
            return download_info['downloadLink']
        else:
            return "Error: Download link not found."
    except requests.exceptions.RequestException as e:
        return f"Error: API request failed - {str(e)}"
    except KeyError:
        return "Error: Unexpected response from the API."

# Function to handle video download and send
async def download_and_send_video(update: Update, context: CallbackContext, download_link: str):
    video_file_path = 'video.mp4'  # Temporary file path for the video

    await update.message.reply_text("Please wait, your video is being processed...")

    try:
        # Faster streaming with chunking
        response = requests.get(download_link, stream=True)
        if response.status_code == 200:
            with open(video_file_path, 'wb') as video_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        video_file.write(chunk)

            # Send the video
            await update.message.reply_text("Your video is ready! Sending it now...")
            await update.message.reply_video(open(video_file_path, 'rb'))

            # Remove file after sending
            os.remove(video_file_path)
        else:
            await update.message.reply_text("Failed to download the video. Please try again.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred while processing the video: {e}")

# Function to extract file ID from the TeraBox mirror URL
def extract_file_id(url):
    for domain in TERABOX_URLS:
        pattern = rf"https?://{domain}/s/([a-zA-Z0-9_-]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# Function to generate the new TeraBoxLink URL
def generate_teraboxlink_url(file_id):
    return f"https://teraboxlink.com/s/{file_id}"

# Command to start and welcome the user
async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    bot: Bot = context.bot
    try:
        # Check membership in the required channel
        member_status = await bot.get_chat_member(FORCE_JOIN_CHANNEL, user.id)
        if member_status.status not in ['member', 'administrator', 'creator']:
            await update.message.reply_text(
                f"Please join the required channel first: {FORCE_JOIN_CHANNEL}\n\n"
                "Once you join, I can help you with the TeraBox file downloads!"
            )
            return
    except Exception as e:
        await update.message.reply_text(
            f"Error: Could not verify your membership in the channel. Ensure you've joined: {FORCE_JOIN_CHANNEL}"
        )
        return

    await update.message.reply_text(
        f"Welcome to the TeraBox Downloader Bot! 👋\n\n"
        f"Developer: {DEVELOPER} ({DEVELOPER_USERNAME})\n\n"
        f"Send me a TeraBox file ID or full URL to get the video directly in the chat.\n"
        f"Example: /download <ID or URL>\n"
        f"If the file is password-protected, provide the password like this: /download <ID> <password>\n"
        f"Supported TeraBox URLs: {', '.join(TERABOX_URLS)}"
    )

# Command to process the download command
async def download(update: Update, context: CallbackContext):
    if context.args:
        url = context.args[0]
        password = context.args[1] if len(context.args) > 1 else ''

        # Match file ID from various TeraBox mirrors
        file_id = None
        for domain in TERABOX_URLS:
            pattern = rf"https?://{domain}/s/([a-zA-Z0-9_-]+)"
            match = re.search(pattern, url)
            if match:
                file_id = match.group(1)
                break

        if not file_id:
            await update.message.reply_text("Invalid TeraBox URL. Please provide a valid link.")
            return

        # Fetch the download link
        download_link = get_download_link(file_id, password)
        if "Error" not in download_link:
            await download_and_send_video(update, context, download_link)
        else:
            await update.message.reply_text(download_link)
    else:
        await update.message.reply_text("Please provide a TeraBox file URL or ID.\nExample: /download https://terabox.com/s/1z57Ii1-U1hp0472eSdw_nX")

# Command to convert TeraBox URL to TeraBoxLink URL
async def convert(update: Update, context: CallbackContext):
    if context.args:
        url = context.args[0]

        # Extract file ID from the provided TeraBox mirror URL
        file_id = extract_file_id(url)

        if file_id:
            # Generate the new TeraBoxLink URL
            new_url = generate_teraboxlink_url(file_id)
            await update.message.reply_text(f"Here is your converted link: {new_url}")
        else:
            await update.message.reply_text("Invalid TeraBox URL. Please provide a valid link.")
    else:
        await update.message.reply_text("Please provide a TeraBox mirror link.\nExample: /convert https://terabox.com/s/1z57Ii1-U1hp0472eSdw_nX")

# Command to check bot's status
async def status(update: Update, context: CallbackContext):
    await update.message.reply_text("Bot is online. Ready to serve your requests!")

# Main function to run the bot
def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Create the Application and pass it the bot token
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers for the commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("download", download))
    application.add_handler(CommandHandler("convert", convert))  # Added the /convert handler
    application.add_handler(CommandHandler("status", status))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
