import asyncio
from app.core.database import AsyncSessionLocal
from app.repositories import app_repo

async def main():
    async with AsyncSessionLocal() as db:
        print("--- Testing search_apps ---")
        apps = await app_repo.search_apps(db)
        for app in apps:
            print(f"ID: {app.id} | Name: {app.name} | Deleted At: {app.deleted_at}")

        print("--- Testing get_featured ---")
        apps = await app_repo.get_featured(db)
        for app in apps:
            print(f"ID: {app.id} | Name: {app.name} | Deleted At: {app.deleted_at}")

        print("--- Testing get_latest ---")
        apps = await app_repo.get_latest(db)
        for app in apps:
            print(f"ID: {app.id} | Name: {app.name} | Deleted At: {app.deleted_at}")

if __name__ == "__main__":
    asyncio.run(main())
