"""Simple Bot to get AQI reading updates.

Usage:
* Use /find <lat> <lng> command to find the nearest station.
* Use /set <station_id> command to subscribe
* Use /unset command to unsubscribe
* Revert to the basic Echobot example (repeats messages) for others.

Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import os
import logging
import datetime

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
AQI_TOKEN = os.environ["AQI_TOKEN"]

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

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


# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(bot, update):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def echo(bot, update):
    """Echo the user message."""
    update.message.reply_text(update.message.text)


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)


def broadcast_reading(bot, job):
    aqi_data = requests.get(
        "http://api.waqi.info/feed/{}/?token={}".format(
            job.context["station"], AQI_TOKEN
        )
    ).json()['data']
    logger.info("Triggered " + str(job.context))
    text = (
        "{} - {}\nAQI: \t*{}*\nPM 2.5 AQI:\t *{}*"
        "\nConcentration: *{}* ug/m3").format(
        aqi_data["city"]["name"], aqi_data["time"]["s"],
        aqi_data["aqi"], aqi_data["iaqi"]["pm25"]["v"],
        aqi_to_concentration(aqi_data["iaqi"]["pm25"]["v"])
    )
    bot.send_message(
        job.context["chat_id"],
        text=text,
        parse_mode="markdown",
        disable_notification=True
    )


def get_nearest_start():
    now = datetime.datetime.now()
    if now.minute < 20:
        return now.replace(minute=20, second=0)
    return (now.replace(minute=20, second=0) +
            datetime.timedelta(hours=1))


def set_notification(bot, update, args, job_queue, chat_data):
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        station = args[0]
        context = {
            "chat_id": chat_id,
            "station": station
        }
        # Remove existing
        if "job" in chat_data:
            job.schedule_removal()
            del chat_data["job"]
        # Add job to queue
        job_queue.run_once(
            broadcast_reading, 5,
            context=context
        )
        job = job_queue.run_repeating(
            broadcast_reading,
            3600,
            first=get_nearest_start(),
            context=context
        )
        chat_data['job'] = job
        update.message.reply_text('Notification successfully set!')

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <station_id>')


def unset(bot, update, chat_data):
    """Remove the job if the user changed their mind."""
    if 'job' not in chat_data:
        update.message.reply_text("You have no active timer")
        return
    job = chat_data["job"]
    job.schedule_removal()
    del chat_data["job"]
    update.message.reply_text('Timer succefully unset!')


def find_station(bot, update, args):
    """Find the nearest station"""
    try:
        lat, lng = float(args[0]), float(args[1])
        data = requests.get(
            "http://api.waqi.info/feed/geo:{:.8f};{:.8f}/?token={}".format(
                lat, lng, AQI_TOKEN
            )
        ).json()['data']
        logger.info("Find station: %f %f", lat, lng)
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
    updater = Updater(BOT_TOKEN)

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
    dp.add_handler(CommandHandler("unset", unset, pass_chat_data=True))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
