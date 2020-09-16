import logging
import validators
import configparser

import pyourls3
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


# Config
config = configparser.ConfigParser()
config.read("config.ini")

LOGGING_FILENAME = config["GENERAL"]["logging_filename"]
SECRET = config["GENERAL"]["secret"]

YOURLS_URL = config["YOURLS"]["url"]
YOURLS_USER = config["YOURLS"]["user"]
YOURLS_PASSWORD = config["YOURLS"]["password"]

TELEGRAM_TOKEN = config["TELEGRAM"]["token"]

# Logging Config
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename=LOGGING_FILENAME,
)

# TELEGRAM Config
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dispatcher = updater.dispatcher
yourls = pyourls3.Yourls(YOURLS_URL, user=YOURLS_USER, passwd=YOURLS_PASSWORD)


def start(update, context):
    """
    # Funktion, that sends a starting message to a new user
    """
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Type info for more information"
    )


def echo(update, context):
    """
    This function handles the hole communication
    """
    msg = update.message.text
    logging.info(f"User: {update.message.chat.username}, Message: {msg}")

    # "info" displays a short tutorial how to create a shortlink
    if msg.lower() == "info":
        info_message = """**Bot for yourls**
First enter the secret.
"stats" get's you overall statistics, "stats shortlink" get's you statistics for a specific shortlink.

To create a shortlink, proceed as follows:
1. type "shortlink"
2. enter your destination URL
3. enter your shortlink (without the domain)
"""
        context.bot.send_message(chat_id=update.effective_chat.id, text=info_message, parse_mode='Markdown')
        return True

    # This authenticates the user
    if msg == SECRET:
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Secret is correct. Authenticated."
        )
        context.chat_data["auth"] = True
    # If the user is not authenticated notify him and stop
    elif "auth" not in context.chat_data:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Secret?")
        return True

    if "mode" not in context.chat_data:
        context.chat_data["mode"] = ""

    # With "stats" the user gets the overall stats from yourls
    # With "stats shortlink" the user gets the stats for the specific shortlink
    if msg.lower().split(" ")[0] == "stats":
        if len(msg.lower().split(" ")) > 1:
            stats = yourls.url_stats(msg.lower().split(" ")[1])
        else:
            stats = yourls.stats()
        context.bot.send_message(chat_id=update.effective_chat.id, text=stats)
        context.chat_data["mode"] = ""
    # This segments handles the creation of the shortlink
    elif msg.lower() == "shortlink" and not context.chat_data["mode"] == "url_dest":
        context.chat_data["mode"] = "url_dest"
        print(f"set mode to: {context.chat_data['mode']}")
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Destination URL"
        )
    elif context.chat_data["mode"] == "url_dest":
        context.chat_data["url_dest"] = msg.lower()

        valid = validators.url(context.chat_data["url_dest"])
        # print("URL valid:", valid)
        if not valid == True:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="URL is not valid. Try again.",
            )
            return True
        print(
            f"url_dest: {context.chat_data['url_dest']}, set mode to: {context.chat_data['mode']}"
        )
        context.chat_data["mode"] = "url_short"
        context.bot.send_message(chat_id=update.effective_chat.id, text="Kurzlink")
    elif context.chat_data["mode"] == "url_short":
        context.chat_data["url_short"] = msg.lower()
        url_short = context.chat_data["url_short"]
        url_dest = context.chat_data["url_dest"]
        print(f"url_short: {url_short}, url_dest: {url_dest}, checking...")
        context.bot.send_message(chat_id=update.effective_chat.id, text="... checking.")
        try:
            yourls.url_stats(url_short)
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Shortlink exists. Try another one.",
            )
            context.chat_data["mode"] = "url_short"
        except:
            try:
                response = yourls.shorten(
                    context.chat_data["url_dest"], context.chat_data["url_short"]
                )
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Shortlink created: {}".format(response["shorturl"]),
                )
            except pyourls3.exceptions.Pyourls3URLAlreadyExistsError:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Error. The Destination URL already exists!",
                )
                print("Pyourls3URLAlreadyExistsError", response)
            except pyourls3.exceptions.Pyourls3APIError:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Unknown Error. Maybe the shortlink already exists.",
                )
                print("Pyourls3APIError", response)
            except:
                print("except. Don't know what's wrong.")
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="except. Don't know what's wrong.",
                )
            finally:
                context.chat_data["mode"] = ""
                context.chat_data["url_short"] = ""
                context.chat_data["url_dest"] = ""

    # context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


# Adding the echo handler to telegram
echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
dispatcher.add_handler(echo_handler)

# Adding the start handler to telegram
start_handler = CommandHandler("start", start)
dispatcher.add_handler(start_handler)

updater.start_polling()
