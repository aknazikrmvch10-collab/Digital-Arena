import asyncio
from aiogram import Bot
import sys

def main():
    token = None
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('BOT_TOKEN='):
                token = line.split('=', 1)[1].strip()
                break
    
    if token:
        bot = Bot(token=token)
        print(asyncio.run(bot.get_me()).username)
    else:
        print("NO TOKEN")

if __name__ == "__main__":
    main()
