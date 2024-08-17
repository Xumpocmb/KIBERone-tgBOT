from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, BranchesTelegramLink


async def orm_add_user(session: AsyncSession, data: dict):
    user = User(
        tg_id=data.get('tg_id'),
        username=data.get('username'),
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        phone_number=data.get('phone_number'),
    )
    session.add(user)
    await session.commit()


async def orm_get_user(session: AsyncSession, tg_id: int):
    query = select(User).where(User.tg_id == tg_id)
    result = await session.execute(query)
    return result.scalar()


async def orm_update_user(session: AsyncSession, user_data: dict):
    try:
        tg_id = user_data.get('tg_id')
        query = update(User).where(User.tg_id == tg_id).values(**user_data)
        await session.execute(query)
        await session.commit()
    except IntegrityError as e:
        print(f"Ошибка целостности данных: {e}")
        await session.rollback()
    except SQLAlchemyError as e:
        print(f"Ошибка SQLAlchemy: {e}")
        await session.rollback()
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")
        await session.rollback()


async def get_branch_tg_link(session: AsyncSession, branch_id: int):
    query = select(BranchesTelegramLink).where(BranchesTelegramLink.branch_id == branch_id)
    result = await session.execute(query)
    return result.scalar()


async def get_all_users(session: AsyncSession):
    query = select(User)
    result = await session.execute(query)
    return result.scalars().all()
