"""Simple Bot to get AQI reading updates.

Usage:
* Use /find <lat> <lng> command to find the nearest station.
* Use /set <station_id> command to subscribe
* Use /unset command to unsubscribe
* Use /get to get the latest reading for the subscribed station
* Revert to the basic Echobot example (repeats messages) for others.

Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import os
import logging
import datetime
from pprint import pprint

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from retrying import retry
import requests
from google.cloud import firestore
from google.oauth2 import service_account

BOT_TOKEN = os.environ["BOT_TOKEN"]
AQI_TOKEN = os.environ["AQI_TOKEN"]
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "keyfile.json"

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

LOGGER = logging.getLogger(__name__)

DB = firestore.Client()

USEPA_PM25_2012 = [
    (0, 50, 0, 12),
    (50, 100, 12.1, 35.4),
    (100, 150, 35.5, 55.4),
    (150, 200, 55.5, 150.4),
    (200, 300, 150.5, 250.4),
    (300, 400, 250.5, 350.4),
    (400, 500, 350.5, 500)
]


def aqi_to_concentration(aqi):
    for ind_l, ind_h, lower, higher in USEPA_PM25_2012:
        if aqi <= ind_h:
            return round(higher - (ind_h - aqi) * (higher - lower) / (ind_h - ind_l))
    return round(aqi)


def load_from_database():
    # Then query for documents
    subscription_ref = DB.collection(u'subscriptions')
    subscriptions = {}
    for doc in subscription_ref.stream():
        subscriptions[doc.id] = doc.to_dict()
    return subscriptions


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text(
        f'Hi! {update.message.from_user.first_name}')


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(bot, update):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def error(bot, update, error):
    """Log Errors caused by Updates."""
    LOGGER.warning('Update "%s" caused error "%s"', update, error)


@retry(stop_max_attempt_number=3, wait_fixed=5000)
def get_reading(station):
    aqi_data = requests.get(
        "http://api.waqi.info/feed/@{}/?token={}".format(
            station, AQI_TOKEN
        )
    ).json()
    if aqi_data["status"] != "ok":
        LOGGER.warning(aqi_data)
        raise RuntimeError("Failed to get the reading from the API server.")
    return aqi_data["data"]


def periodic_status_update(context: CallbackContext):
    subscriptions = load_from_database()
    for chat_id, data in subscriptions.items():
        if "station" in data:
            send_reading(context.bot, int(chat_id), data["station"])


def send_reading(bot, chat_id, station: str):
    aqi_data = get_reading(station)
    text = (
        "{} - {}\nAQI: \t*{}*\nPM 2.5 AQI:\t *{}*"
        "\nConcentration: *{}* ug/m3").format(
        aqi_data["city"]["name"], aqi_data["time"]["s"],
        aqi_data["aqi"], aqi_data["iaqi"]["pm25"]["v"],
        aqi_to_concentration(aqi_data["iaqi"]["pm25"]["v"])
    )
    bot.send_message(
        chat_id,
        text=text,
        parse_mode="markdown",
        disable_notification=aqi_data["aqi"] <= 100
    )


def get_nearest_start():
    now = datetime.datetime.now()
    if now.minute < 20:
        return now.replace(minute=20, second=0)
    return (now.replace(minute=20, second=0) +
            datetime.timedelta(hours=1))


def set_notification(update, context):
    """Set a station to be tracked"""
    chat_id = update.message.chat_id
    try:
        station = context.args[0]
        doc_ref = DB.collection('subscriptions').document(str(chat_id))
        doc_ref.set({
            "set_by": update.message.from_user.id,
            "station": station
        })
        update.message.reply_text('Notification successfully set!')
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <station_id>')


def unset(update, context):
    """Remove the tracking station."""
    chat_id = update.message.chat_id
    doc_ref = DB.collection('subscriptions').document(str(chat_id))
    doc_ref.set({
        "set_by": update.message.from_user.id
    })
    update.message.reply_text('Notification succefully unset!')


def on_demand_broadcast(update, context):
    chat_id = update.message.chat_id
    data = DB.collection('subscriptions').document(str(chat_id)).get()
    if data.exists is False or "station" not in data.to_dict():
        update.message.reply_text('You need to /set a station first!')
    else:
        send_reading(context.bot, chat_id, data.get("station"))


def find_station(update, context):
    """Find the nearest station"""
    try:
        lat, lng = float(context.args[0]), float(context.args[1])
        data = requests.get(
            "http://api.waqi.info/feed/geo:{:.8f};{:.8f}/?token={}".format(
                lat, lng, AQI_TOKEN
            )
        ).json()['data']
        LOGGER.info("Find station: %f %f %s", lat, lng, data)
        update.message.reply_text(
            "name: {} @ {};{} \n"
            "id: {}\n"
            "link: {}\n"
            "authority: {}".format(
                data["city"]["name"],
                data["city"]["geo"][0],
                data["city"]["geo"][1],
                data["idx"],
                data["city"]["url"],
                data["attributions"][0]["name"]
            )
        )
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /find <lat> <lng>')


def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(BOT_TOKEN, use_context=True)
    job_queue = updater.job_queue

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("set", set_notification,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    dp.add_handler(CommandHandler("find", find_station,
                                  pass_args=True))
    dp.add_handler(CommandHandler("get", on_demand_broadcast,
                                  pass_chat_data=True))
    dp.add_handler(CommandHandler("unset", unset, pass_chat_data=True))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    job_queue.run_repeating(
        periodic_status_update, interval=3600, first=get_nearest_start()
    )

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
