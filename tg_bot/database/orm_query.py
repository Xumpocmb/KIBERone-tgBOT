from oauthlib.uri_validate import query
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from tg_bot.database.models import SchedulerTask, User, BranchesTelegramLink, Manager, Locations


async def orm_add_user(session: AsyncSession, data: dict):
    try:
        user = User(
            tg_id=data.get('tg_id'),
            username=data.get('username'),
            phone_number=data.get('phone_number'),
            user_branch_ids = data.get("user_branch_ids"),
            user_crm_id = data.get("user_crm_id"),
            user_lessons = data.get("user_lessons"),
            is_study = data.get("is_study"),
            customer_data = data.get("customer_data")
        )
        session.add(user)
        await session.commit()
    except Exception as e:
        await session.rollback()
        print(f"An error occurred: {e}")


async  def orm_get_location(session: AsyncSession, room_id: int):
    try:
        query = select(Locations).where(Locations.location_id == room_id)
        result = await session.execute(query)
        location = result.scalar()
        if location:
            logger.info(f"Локация с room_id {room_id} найдена: {location}")
        else:
            logger.info(f"Локация с room_id {room_id} не найдена.")
        return location
    except Exception as e:
        print(f"An error occurred: {e}")


async def orm_get_user_by_tg_id(session: AsyncSession, tg_id: int):
    try:
        query = select(User).where(User.tg_id == tg_id)
        result = await session.execute(query)
        user = result.scalar()
        if user:
            logger.info(f"Пользователь с tg_id {tg_id} найден: {user}")
        else:
            logger.info(f"Пользователь с tg_id {tg_id} не найден.")
        return user
    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при получении пользователя с tg_id {tg_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Неизвестная ошибка при получении пользователя с tg_id {tg_id}: {e}")
        return None


async def orm_get_user_by_crm_id(session: AsyncSession, crm_id: int):
    try:
        query = select(User).where(User.user_crm_id == crm_id)
        result = await session.execute(query)
        user = result.scalar()
        if user:
            logger.info(f"Пользователь с crm_id {crm_id} найден: {user}")
        else:
            logger.info(f"Пользователь с crm_id {crm_id} не найден.")
        return user
    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при получении пользователя с tg_id {crm_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Неизвестная ошибка при получении пользователя с tg_id {crm_id}: {e}")
        return None


async def orm_update_user(session: AsyncSession, user_data: dict):
    try:
        tg_id = user_data.get('tg_id')
        query = update(User).where(User.tg_id == tg_id).values(**user_data)
        await session.execute(query)
        await session.commit()
        logger.info(f"Пользователь с tg_id {tg_id} успешно обновлен данными: {user_data}")

    except IntegrityError as e:
        logger.error(f"Ошибка целостности данных: {e}")
        await session.rollback()
    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy: {e}")
        await session.rollback()
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        await session.rollback()


async def get_branch_tg_link(session: AsyncSession, branch_id: int):
    try:
        query = select(BranchesTelegramLink).where(BranchesTelegramLink.branch_id == branch_id)
        result = await session.execute(query)
        link = result.scalar()
        if link:
            logger.info(f"Получена ссылка для branch_id {branch_id}: {link}")
        else:
            logger.info(f"Ссылка для branch_id {branch_id} не найдена.")
        return link
    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при получении ссылки для branch_id {branch_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Неизвестная ошибка при получении ссылки для branch_id {branch_id}: {e}")
        return None


async def get_all_users(session: AsyncSession):
    try:
        query = select(User)
        result = await session.execute(query)
        users = result.scalars().all()
        logger.info(f"Получено {len(users)} пользователей из базы данных.")
        return users
    except SQLAlchemyError as e:
        logger.error(f"Ошибка SQLAlchemy при получении пользователей: {e}")
        return []
    except Exception as e:
        logger.error(f"Неизвестная ошибка при получении пользователей: {e}")
        return []


async def get_manager_info(session: AsyncSession, location_id: int):
    try:
        query = select(Manager).where(Manager.location == location_id)
        result = await session.execute(query)
        manager = result.scalar()
        if manager is None:
            logger.warning(f"Менеджер с location_id {location_id} не найден.")
        return manager
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при выполнении запроса: {e}")
        return None


async def get_tasks(session: AsyncSession):
    try:
        query = select(SchedulerTask)
        result = await session.execute(query)
        tasks = result.scalars().all()
        logger.info(f"Получено {len(tasks)} задач.")
        return tasks
    except SQLAlchemyError as e:
        logger.error(f"Ошибка при выполнении запроса: {e}")
        return []
    except Exception as e:
        logger.error(f"Неизвестная ошибка при получении задач: {e}")
        return []
