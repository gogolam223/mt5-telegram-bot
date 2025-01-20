from src.telegram_bot import TelegramBot
import json
import asyncio

if __name__ == "__main__":
    with open('config.json', 'r') as file:
        config = json.load(file)
    bot = TelegramBot(config)
    try:
        # asyncio.run(bot.print_telegram_channals())
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\nBot stopped.")