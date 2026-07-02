import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.app import App, AppVersion
from app.models.log import Download
from app.core.config import settings

async def seed_downloads():
    print("Seeding download statistics logs...")
    async with AsyncSessionLocal() as db:
        # Get Super Admin user
        admin_email = settings.SUPERADMIN_EMAIL
        q = select(User).where(User.email == admin_email)
        res = await db.execute(q)
        admin_user = res.scalar_one_or_none()
        if not admin_user:
            print("Super Admin user not found! Run seed_categories.py or start the system first.")
            return

        # Get all apps
        apps_res = await db.execute(select(App).where(App.deleted_at.is_(None)))
        apps = apps_res.scalars().all()
        if not apps:
            print("No apps found in the database. Please register an app first to seed download stats.")
            return

        for app in apps:
            # Get latest version
            versions_res = await db.execute(
                select(AppVersion)
                .where(AppVersion.app_id == app.id, AppVersion.deleted_at.is_(None))
                .order_by(AppVersion.created_at.desc())
            )
            version = versions_res.scalars().first()
            if not version:
                print(f"Skipping app '{app.name}' as it has no versions/releases.")
                continue

            # Seed 15 completed downloads spread across the last 5 days
            base_time = datetime.now(timezone.utc)
            for i in range(15):
                day_offset = i % 5
                dl_time = base_time - timedelta(days=day_offset, hours=i * 2)
                dl = Download(
                    user_id=admin_user.id,
                    app_id=app.id,
                    version_id=version.id,
                    ip_address=f"192.168.1.{10 + i}",
                    device_info="Mozilla/5.0 (Android; Mobile)",
                    status="completed",
                    created_at=dl_time,
                    updated_at=dl_time
                )
                db.add(dl)
                print(f"Seeded download log for app '{app.name}' on {dl_time.date()}")

        await db.commit()
    print("Download statistics logs seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed_downloads())
