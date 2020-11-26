import validators
import logging

from pyourls3 import exceptions, Yourls
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

import requests

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename="bot.log",
)

class YourlsBot:
    def __init__(
            self, yourls_url, yourls_user, yourls_password, telegram_token, secret
    ):
        self.secret = secret
        self.yourls = Yourls(
            yourls_url, user=yourls_user, passwd=yourls_password
        )
        self.updater = Updater(token=telegram_token, use_context=True)
        self.dispatcher = self.updater.dispatcher

        # info-handler
        info_handler = MessageHandler(Filters.text('info'), self.info)
        self.dispatcher.add_handler(info_handler)

        # update-handler
        update_handler = MessageHandler(Filters.regex(r'update'), self.update)
        self.dispatcher.add_handler(update_handler)

        # delete-handler
        delete_handler = MessageHandler(Filters.regex(r'delete'), self.delete)
        self.dispatcher.add_handler(delete_handler)

        # secret-handler
        secret_handler = MessageHandler(Filters.text(self.secret), self.check_secret)
        self.dispatcher.add_handler(secret_handler)

        # stats-handler
        stats_handler = MessageHandler(Filters.regex(r'stats'), self.stats)
        self.dispatcher.add_handler(stats_handler)

        # shortlink-handler
        shortlink_handler = MessageHandler(Filters.regex(r'shortlink'), self.shortlink)
        self.dispatcher.add_handler(shortlink_handler)

        # echo-handler
        echo_handler = MessageHandler(Filters.text & (~Filters.command), self.echo)
        self.dispatcher.add_handler(echo_handler)

        # Adding the start handler to telegram
        start_handler = CommandHandler("start", self.start)
        reset_handler = CommandHandler("reset", self.reset)
        self.dispatcher.add_handler(start_handler)
        self.dispatcher.add_handler(reset_handler)

        self.updater.start_polling()

    def jsonToMessage(self, msg_json):
        """ Converts a Dict/JSON to a Message """
        if type(msg_json) == str:
            return msg_json
        reply_message = ""
        for item in msg_json:
            reply_message += f"{item}: {msg_json[item]}\n"
        return reply_message

    def start(self, update, context):
        """
        Funktion, that sends a starting message to a new user
        """
        context.bot.send_message(
            chat_id=update.effective_chat.id, text="Type info for more information"
        )

    def info(self, update, context):
        """
        Funktion, that sends a starting message to a new user
        """

        info_message = '''**Bot for yourls**
            First enter the secret.
            "stats" get's you overall statistics, "stats shortlink" get's you statistics for a specific shortlink.
            "delete <shortlink>" deletes a shortlink.
            To create a shortlink, proceed as follows:
            1. type "shortlink"
            2. enter your destination URL
            3. enter your shortlink (without the domain)
            OR:
            type "shortlink <destination>"
            OR:
            type "shortlink <short> <destination>"
            '''
        logging.info(f"User: {update.message.chat.username}, Message: {update.message.text}")

        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=info_message,
            parse_mode="Markdown",
        )

    def reset(self, update, context):
        context.chat_data["mode"] = ""
        context.bot.send_message(chat_id=update.effective_chat.id, text="mode reset.")

    def delete(self, update, context):
        # Needed: Check, if the shortlink exist.
        if "auth" not in context.chat_data:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Secret?")
            return True
        msg = update.message.text

        logging.info(f"User: {update.message.chat.username}, Message: {msg}")
        if len(msg.lower().split(" ")) > 1:
            try:
                response = self.yourls.delete(msg.lower().split(" ")[1])
                context.bot.send_message(chat_id=update.effective_chat.id, text="Deleted.")
            except exceptions.Pyourls3HTTPError:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Not found.")

    def update(self, update, context):
        # Needed: Check, if the shortlink exist.
        if "auth" not in context.chat_data:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Secret?")
            return True
        msg = update.message.text

        logging.info(f"User: {update.message.chat.username}, Message: {msg}")
        if len(msg.lower().split(" ")) > 2:
            try:
                response = self.yourls.update(msg.lower().split(" ")[1],msg.lower().split(" ")[1])
                context.bot.send_message(chat_id=update.effective_chat.id, text="Updated.")
            except exceptions.Pyourls3HTTPError:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Not found.")
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text="You need to specify two arguments: update <shortlink> <destination>")

    def stats(self, update, context):
        # With "stats" the user gets the overall stats from yourls
        # With "stats shortlink" the user gets the stats for the specific shortlink
        if "auth" not in context.chat_data:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Secret?")
            return
        msg = update.message.text.lower()
        logging.info(f"User: {update.message.chat.username}, Message: {msg}")

        if len(msg.split(" ")) > 1:
            shortlink = msg.split(" ")[1]
            try:
                stats = self.yourls.url_stats(shortlink)
                reply_message = self.jsonToMessage(stats)
            except:
                reply_message = f"Shortlink {shortlink} was not found!"
        else:
            stats = self.yourls.stats()
            reply_message = self.jsonToMessage(stats)


        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=reply_message,
            disable_web_page_preview=True,
        )
        context.chat_data["mode"] = ""


    def shortlink(self, update, context):
        # This segments handles the creation of the shortlink
        if "auth" not in context.chat_data:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Secret?")
            return True
        msg = update.message.text.lower()
        logging.info(f"User: {update.message.chat.username}, Message: {msg}")
        msg_splitted = msg.split()

        if len(msg.split()) > 1:
            msg_splitted = msg.split()
            if len(msg_splitted) == 2:
                context.chat_data["url_dest"] = msg_splitted[1]
                valid = validators.url(context.chat_data["url_dest"])
                # print("URL valid:", valid)
                if not valid == True:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="URL is not valid. Try again.",
                    )
                    return True
                context.chat_data["mode"] = "just_dest"
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text=self.createShortLink(context)
                )
            elif len(msg_splitted) == 3:
                context.chat_data["url_short"] = msg_splitted[1]
                context.chat_data["url_dest"] = msg_splitted[2]
                valid = validators.url(context.chat_data["url_dest"])
                # print("URL valid:", valid)
                if not valid == True:
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="URL is not valid. Try again.",
                    )
                    return True
                context.chat_data["mode"] = "both_urls"
                context.bot.send_message(
                    chat_id=update.effective_chat.id, text=self.createShortLink(context)
                )

        else:
            context.chat_data["mode"] = "url_dest"
            print(f"set mode to: {context.chat_data['mode']}")
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="Destination URL"
            )

    def check_secret(self, update, context):
        if update.message.text == self.secret:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Secret is correct. Authenticated.",
            )
            context.chat_data["auth"] = True

    def echo(self, update, context):
        """
        This function handles the hole communication
        """
        msg = update.message.text
        logging.info(f"User: {update.message.chat.username}, Message: {msg}")
        print(f"User: {update.message.chat.username}, Message: {msg}")

        # If the user is not authenticated notify him and stop
        if "auth" not in context.chat_data:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Secret?")
            return True

        if "mode" not in context.chat_data:
            context.chat_data["mode"] = ""
        if context.chat_data["mode"] == "url_dest":
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
            context.chat_data["mode"] = "both_urls"
            print(f"url_short: {url_short}, url_dest: {url_dest}, checking...")
            context.bot.send_message(
                chat_id=update.effective_chat.id, text="... checking."
            )

            try:
                self.yourls.url_stats(url_short)
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Shortlink exists. Try another one.",
                )
                context.chat_data["mode"] = "url_short"
            except:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=self.createShortLink(context),
                )

        # context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

    def createShortLink(self, context):
        try:
            if context.chat_data["mode"] == "both_urls":
                response = self.yourls.shorten(
                    context.chat_data["url_dest"], context.chat_data["url_short"]
                )
            elif context.chat_data["mode"] == "just_dest":
                response = self.yourls.shorten(context.chat_data["url_dest"])
            return_msg = "Shortlink created: {}".format(
                response["shorturl"], disable_web_page_preview=True
            )
        except pyourls3.exceptions.Pyourls3URLAlreadyExistsError:
            return_msg = "Error. The Destination URL already exists!"
            # print("Pyourls3URLAlreadyExistsError", response)
        except pyourls3.exceptions.Pyourls3APIError:
            return_msg = "Unknown Error. Maybe the shortlink already exists."
            # print("Pyourls3APIError", response)
        except:
            return_msg = "except. Don't know what's wrong."
            print("except. Don't know what's wrong.")
        finally:
            context.chat_data["mode"] = ""
            context.chat_data["url_short"] = ""
            context.chat_data["url_dest"] = ""

        return return_msg


if __name__ == "__main__":
    import configparser

    # Config
    config = configparser.ConfigParser()
    config.read("config.ini")

    LOGGING_FILENAME = config["GENERAL"]["logging_filename"]
    SECRET = config["GENERAL"]["secret"]

    YOURLS_URL = config["YOURLS"]["url"]
    YOURLS_USER = config["YOURLS"]["user"]
    YOURLS_PASSWORD = config["YOURLS"]["password"]

    TELEGRAM_TOKEN = config["TELEGRAM"]["token"]

    yourlsBot = YourlsBot(
        YOURLS_URL, YOURLS_USER, YOURLS_PASSWORD, TELEGRAM_TOKEN, SECRET
    )