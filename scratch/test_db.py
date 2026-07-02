import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.app import App
from app.schemas.app import AppDetailResponse

async def test():
    async with AsyncSessionLocal() as db:
        # Fetch an app
        q = select(App).limit(1)
        res = await db.execute(q)
        app = res.scalar_one_or_none()
        if not app:
            print("No app found")
            return
        
        print("Fetched app, now refreshing relationships...")
        await db.refresh(app, ["category", "versions"])
        print("Successfully refreshed! Validating model...")
        
        # Try validating
        app_res = AppDetailResponse.model_validate(app)
        print("Validation succeeded!", app_res.name, app_res.category.name, len(app_res.versions))

if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.getcwd())
    asyncio.run(test())
