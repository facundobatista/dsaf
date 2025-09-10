from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

engine = create_async_engine("sqlite+aiosqlite:///storage.db")

# Session asincrónica
AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

# Base para los modelos
Base = declarative_base()


class Device(Base):
    __tablename__ = "devices"

    name = Column(String, primary_key=True, index=True)
    last_report_content = Column(JSON, nullable=True)
    last_report_date = Column(DateTime, nullable=True)

    def to_dict(self):
        """Return a dictionary with all the model's info."""
        return dict(
            name=self.name,
            last_report_content=self.last_report_content,
            last_report_date=self.last_report_date,
        )


async def init_db():
    """Init DB and create tables if not present."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    # debug / manual / test mode

    import asyncio
    import datetime
    import uuid

    from sqlalchemy import select

    async def otra():
        print("foo")

    async def test():
        await otra()
        await init_db()

        async with AsyncSession() as session:
            newname = "test-" + uuid.uuid4().hex[:10]
            new_device = Device(
                name=newname, last_report_content={}, last_report_date=datetime.datetime.now())
            session.add(new_device)
            await session.commit()

        async with AsyncSession() as session:
            stmt = select(Device).where(Device.name == "foo")
            result = await session.scalars(stmt)
            print("===== result", result)
            for item in result:
                print("======= item", (item.name, item.last_report_date))

        async with AsyncSession() as session:
            stmt = select(Device).where(Device.name == "foo2")
            result = await session.execute(stmt)
            device = result.scalars().one()
            print("===== dev", device.name, device.last_report_date)

            device.last_report_date = datetime.datetime.now()
            await session.commit()

    asyncio.run(test())
