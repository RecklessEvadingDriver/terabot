import logging
import requests
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext
import os
import re

# Replace with your own bot token
TELEGRAM_TOKEN = '7509017987:AAEfiGeSmNViCdT32sG1wPCX7b10fNxH6mQ'

# Channel to force join
FORCE_JOIN_CHANNEL = 'https://t.me/AnotherHappyboy'

# Developer details
DEVELOPER = "Reckless"
DEVELOPER_USERNAME = "@recklessevader"

# TeraBox URLs
TERABOX_URLS = [
    "www.mirrobox.com", "www.nephobox.com", "freeterabox.com", "www.freeterabox.com", 
    "1024tera.com", "4funbox.co", "www.4funbox.com", "mirrobox.com", "nephobox.com", 
    "terabox.app", "terabox.com", "www.terabox.app", "terabox.fun", "www.terabox.com", 
    "www.1024tera.com", "www.momerybox.com", "teraboxapp.com", "momerybox.com", 
    "tibibox.com", "www.tibibox.com", "www.teraboxapp.com"
]

# Function to call the first API
def get_terabox_info(file_id, password=''):
    api_url = f"https://terabox.hnn.workers.dev/api/get-info?shorturl={file_id}&pwd={password}"
    response = requests.get(api_url)
    if response.status_code != 200:
        return None
    return response.json()

# Function to call the second API for the download link
def get_download_link(file_id, password=''):
    info = get_terabox_info(file_id, password)
    if not info or 'list' not in info or len(info['list']) == 0:
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
    
    download_response = requests.post(download_api_url, json=post_data, headers=headers)
    if download_response.status_code != 200:
        return "Error: Unable to retrieve download link."
    
    download_info = download_response.json()
    if 'downloadLink' in download_info:
        return download_info['downloadLink']
    else:
        return "Error: Download link not found."

# Function to download video and send it via Telegram
async def download_and_send_video(update: Update, context: CallbackContext, download_link: str):
    video_file_path = 'video.mp4'  # Temporary file path for the video

    await update.message.reply_text("Please wait, your video is being processed...")

    # Download the video
    response = requests.get(download_link, stream=True)
    if response.status_code == 200:
        with open(video_file_path, 'wb') as video_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    video_file.write(chunk)

        # Send the video to Telegram
        await update.message.reply_text("Your video is ready! Sending it now...")
        await update.message.reply_video(open(video_file_path, 'rb'))

        # Remove the video file after sending
        os.remove(video_file_path)
    else:
        await update.message.reply_text("Failed to download the video. Please try again.")

# Command handler to start the bot and explain how to use it
async def start(update: Update, context: CallbackContext):
    # Check if user is a member of the required channel
    user = update.message.from_user
    bot: Bot = context.bot
    try:
        # Check if user is a member of the channel
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

# Command handler to process the download command
async def download(update: Update, context: CallbackContext):
    if context.args:
        # Extract file ID or full URL and optional password
        url = context.args[0]
        password = context.args[1] if len(context.args) > 1 else ''
        
        # Try to match the TeraBox short link (e.g., teraboxapp.xyz/s/XXXXXX)
        match = re.search(r'terabox(?:app|link)\.xyz/s/([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
        else:
            # If not a short link, check if it's a full TeraBox URL with a different format
            match = re.search(r's/([a-zA-Z0-9_-]+)', url)
            if match:
                file_id = match.group(1)
            else:
                await update.message.reply_text("Invalid TeraBox URL. Please provide a valid link.")
                return

        # Fetch the download link using the file ID and password if provided
        download_link = get_download_link(file_id, password)
        if "Error" not in download_link:
            await download_and_send_video(update, context, download_link)
        else:
            await update.message.reply_text(download_link)
    else:
        await update.message.reply_text("Please provide the TeraBox file URL or ID.\nExample: /download https://teraboxapp.xyz/s/1z57Ii1-U1hp0472eSdw_nX")

# Admin command to check the bot's status
async def status(update: Update, context: CallbackContext):
    await update.message.reply_text("Bot is online. Ready to serve your requests!")

# Main function to start the bot
def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Create the Application and pass it the bot token
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers for the commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("download", download))
    application.add_handler(CommandHandler("status", status))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
