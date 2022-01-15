from django.conf import settings


async def log_send(*, bot, message):

    logger_channel = bot.get_channel(int(settings.LOG_CHANNEL_ID))

    await logger_channel.send(message)
