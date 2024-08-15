from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[str] = mapped_column(unique=True)
    first_name: Mapped[str] = mapped_column(nullable=True)
    last_name: Mapped[str] = mapped_column(nullable=True)
    username: Mapped[str] = mapped_column(nullable=True)
    phone_number: Mapped[str] = mapped_column(nullable=True)
    balance: Mapped[float] = mapped_column(default=0.0, nullable=True)
    is_student: Mapped[int] = mapped_column(default=0, nullable=True)
    lesson_date: Mapped[str] = mapped_column(nullable=True)
    notified: Mapped[bool] = mapped_column(default=True)

    def __repr__(self):
        return f"<User(id={self.id}, tg_id={self.tg_id}, username={self.username})>"


class BranchesTelegramLink(Base):
    __tablename__ = "branches_telegram_link"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    branch_id: Mapped[int] = mapped_column()
    link: Mapped[str] = mapped_column()

    def __repr__(self):
        return f"<BranchTelegramLinks(id={self.id}, branch_id={self.branch_id}, link={self.link})>"
