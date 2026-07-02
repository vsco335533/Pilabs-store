import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.app import App

async def update_package():
    async with AsyncSessionLocal() as db:
        q = select(App).where(App.name == "Karsha")
        res = await db.execute(q)
        app = res.scalar_one_or_none()
        
        if app:
            print(f"Found app '{app.name}' with package_name '{app.package_name}'")
            app.package_name = "com.karsha.app"
            print(f"Updating package_name to 'com.karsha.app'...")
            await db.commit()
            print("Successfully updated database!")
        else:
            print("App 'Karsha' not found in the database.")

if __name__ == '__main__':
    asyncio.run(update_package())
