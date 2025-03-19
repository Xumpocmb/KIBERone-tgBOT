from datetime import datetime
from sqlalchemy import LargeBinary, ForeignKey
from sqlalchemy import DateTime, func, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, foreign, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[str] = mapped_column(unique=True)
    first_name: Mapped[str] = mapped_column(nullable=True)
    last_name: Mapped[str] = mapped_column(nullable=True)
    username: Mapped[str] = mapped_column(nullable=True)
    phone_number: Mapped[str] = mapped_column(nullable=True)

    is_study: Mapped[int] = mapped_column(default=0, nullable=True)
    balance: Mapped[str] = mapped_column(default="0", nullable=True)
    paid_lesson_count: Mapped[int] = mapped_column(default=0, nullable=True)
    next_lesson_date: Mapped[str] = mapped_column(nullable=True)
    user_branch_ids: Mapped[str] = mapped_column(nullable=True)
    user_crm_id: Mapped[int] = mapped_column(nullable=True)
    user_lessons: Mapped[bool] = mapped_column(nullable=True)

    customer_data: Mapped[str] = mapped_column(nullable=True)

    notified: Mapped[bool] = mapped_column(default=False, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=func.now())

    kiberons_count: Mapped[int] = mapped_column(default=0, nullable=True)
    kiberons_count_after_orders: Mapped[int] = mapped_column(default=0, nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, tg_id={self.tg_id}, username={self.username})>"


class BranchesTelegramLink(Base):
    __tablename__ = "branches_telegram_link"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    branch_id: Mapped[int] = mapped_column()
    link: Mapped[str] = mapped_column()

    def __repr__(self):
        return f"<BranchTelegramLinks(id={self.id}, branch_id={self.branch_id}, link={self.link})>"


class FAQ(Base):
    __tablename__ = "FAQ"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column()
    answer: Mapped[str] = mapped_column()

    def __repr__(self):
        return f"<FAQ(id={self.id}, question={self.question}, answer={self.answer})>"


class Promotion(Base):
    __tablename__ = "Promotion"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column()
    answer: Mapped[str] = mapped_column()

    def __repr__(self):
        return f"<Promotion(id={self.id}, title={self.question}, content={self.answer})>"


class PartnerCategory(Base):
    __tablename__ = "PartnerCategory"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column()

    def __repr__(self):
        return f"<PartnerCategory(id={self.id}, name={self.category})>"


class Partner(Base):
    __tablename__ = "Partner"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    partner: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    category_id: Mapped[int] = mapped_column(ForeignKey('PartnerCategory.id'))
    category: Mapped[PartnerCategory] = relationship("PartnerCategory", backref="partners")

    def __repr__(self):
        return f"<Partner(id={self.id}, name={self.partner}, link={self.description})>"


class Contact(Base):
    __tablename__ = "Contact"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    Contact: Mapped[str] = mapped_column()
    Contact_link: Mapped[str] = mapped_column()

    def __repr__(self):
        return f"<Contact(id={self.id}, Contact={self.Contact}, Contact_link={self.Contact_link})>"


class Link(Base):
    __tablename__ = "Link"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    link_name: Mapped[str] = mapped_column()
    link_url: Mapped[str] = mapped_column()

    def __repr__(self):
        return f"<Link(id={self.id}, name={self.link_name}, link={self.link_url})>"


class Manager(Base):
    __tablename__ = "Manager"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    branch: Mapped[int] = mapped_column()
    location: Mapped[int] = mapped_column()
    manager: Mapped[str] = mapped_column()
    link: Mapped[str] = mapped_column()

    def __repr__(self):
        return f"<Manager(id={self.id}, city={self.branch}, manager={self.manager}, link={self.link})>"


class SchedulerTask(Base):
    __tablename__ = "apscheduler_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    next_run_time: Mapped[float] = mapped_column()
    job_state: Mapped[bytes] = mapped_column(LargeBinary)

    def __repr__(self):
        return f"<Tasks(id={self.id}, name={self.task_name}, link={self.task_link})>"


class Locations(Base):
    __tablename__ = "Locations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    location_branch_id: Mapped[int] = mapped_column()
    location_id: Mapped[int] = mapped_column()
    location_name: Mapped[str] = mapped_column()
    location_map_link: Mapped[str] = mapped_column()
    sheet_url: Mapped[str] = mapped_column()
    sheet_names: Mapped[str] = mapped_column()

    def __repr__(self):
        return f"<Locations(id={self.id}, name={self.location_name})>"

