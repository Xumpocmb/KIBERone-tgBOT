from loguru import logger

logger.add("debug.log", format="{time} {level} {message}", level="ERROR", rotation="1 MB", compression="zip")


async def check_user_statuses_in_crm():
    logger.info('Проверка статусов пользователей..')
    logger.info('Проверка статусов пользователей завершена.')