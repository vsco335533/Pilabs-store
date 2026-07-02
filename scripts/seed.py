import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from slugify import slugify

from app.core.database import AsyncSessionLocal
from app.models.role import Role, Permission
from app.models.user import User
from app.models.app import Category, App, AppVersion
from app.security.security import get_password_hash
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_data():
    async with AsyncSessionLocal() as db:
        logger.info("Starting database seeding...")

        # 1. Seed Permissions
        permissions_list = [
            {"name": "manage_apps", "description": "Create, update, disable, delete applications"},
            {"name": "manage_users", "description": "View, activate, deactivate system users"},
            {"name": "view_analytics", "description": "Access dashboard stats and charts"},
            {"name": "download_apps", "description": "Download and install applications"},
        ]
        
        db_permissions = {}
        for perm in permissions_list:
            q = select(Permission).where(Permission.name == perm["name"])
            res = await db.execute(q)
            db_perm = res.scalar_one_or_none()
            if not db_perm:
                db_perm = Permission(**perm)
                db.add(db_perm)
                await db.flush()
                logger.info(f"Created permission: {perm['name']}")
            db_permissions[perm["name"]] = db_perm

        # 2. Seed Roles
        roles_list = {
            "Super Admin": ["manage_apps", "manage_users", "view_analytics", "download_apps"],
            "Admin": ["manage_apps", "view_analytics", "download_apps"],
            "User": ["download_apps"],
            "Guest": []
        }

        db_roles = {}
        from sqlalchemy.orm import selectinload
        for role_name, perms in roles_list.items():
            q = select(Role).where(Role.name == role_name).options(selectinload(Role.permissions))
            res = await db.execute(q)
            db_role = res.scalar_one_or_none()
            if not db_role:
                db_role = Role(
                    name=role_name,
                    description=f"{role_name} System Role",
                    permissions=[db_permissions[p] for p in perms]
                )
                db.add(db_role)
                await db.flush()
                logger.info(f"Created role: {role_name}")
            else:
                db_role.permissions = [db_permissions[p] for p in perms]
                db.add(db_role)
                await db.flush()
            db_roles[role_name] = db_role

        # 3. Seed Super Admin User
        admin_email = settings.SUPERADMIN_EMAIL
        q = select(User).where(User.email == admin_email)
        res = await db.execute(q)
        admin_user = res.scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                full_name="System Super Admin",
                email=admin_email,
                phone_number="+10000000000",
                password_hash=get_password_hash(settings.SUPERADMIN_PASSWORD),
                is_active=True,
                is_verified=True,
                role_id=db_roles["Super Admin"].id
            )
            db.add(admin_user)
            await db.flush()
            logger.info(f"Created Super Admin user: {admin_email}")
        
        # 4. Seed Categories
        categories = [
            {"name": "Fintech", "description": "Financial and transaction utility applications"},
            {"name": "Grievance Redressal", "description": "Complaint reporting and citizen support utilities"},
            {"name": "Utilities", "description": "General tools and utility software"}
        ]
        
        db_categories = {}
        for cat in categories:
            slug = slugify(cat["name"])
            q = select(Category).where(Category.slug == slug)
            res = await db.execute(q)
            db_cat = res.scalar_one_or_none()
            if not db_cat:
                db_cat = Category(name=cat["name"], slug=slug, description=cat["description"], created_by=admin_user.id)
                db.add(db_cat)
                await db.flush()
                logger.info(f"Created Category: {cat['name']}")
            db_categories[cat["name"]] = db_cat

        # 5. Seed Applications (Karsha & Grievance)
        apps_to_seed = [
            {
                "name": "Karsha",
                "package_name": "com.karsha.pay",
                "developer": "Karsha Technologies",
                "description": "Secure financial payments app enabling swift, encrypted payments, digital receipts, and real-time transaction history tracking.",
                "logo_url": "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=150&h=150&fit=crop", # placeholders, can generate images later
                "screenshots": [
                    "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=400&h=800&fit=crop",
                    "https://images.unsplash.com/photo-1563013544-824ae1d704d3?w=400&h=800&fit=crop"
                ],
                "category": "Fintech",
                "version": {
                    "version_code": 1,
                    "version_name": "1.0.0",
                    "apk_url": "/static/apks/karsha-1.0.0.apk",
                    "apk_size": 24500000, # 24.5MB
                    "release_notes": "Initial enterprise release of Karsha App.",
                    "min_sdk_version": "21",
                    "permissions": ["CAMERA", "INTERNET", "ACCESS_FINE_LOCATION"],
                    "sha256": "4a737f2a1a8c3d9df65961d70e4c6e3b5e36e4b8737f2a1a8c3d9df65961d7a"
                }
            },
            {
                "name": "Grievance",
                "package_name": "com.grievance.app",
                "developer": "Citizen Portal Inc.",
                "description": "Official portal for submitting civic issues and reporting grievances. Track complaint lifecycles and connect directly with local resolution committees.",
                "logo_url": "https://images.unsplash.com/photo-1512428559087-560fa5ceab42?w=150&h=150&fit=crop",
                "screenshots": [
                    "https://images.unsplash.com/photo-1512428559087-560fa5ceab42?w=400&h=800&fit=crop",
                    "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=400&h=800&fit=crop"
                ],
                "category": "Grievance Redressal",
                "version": {
                    "version_code": 1,
                    "version_name": "1.0.0",
                    "apk_url": "/static/apks/grievance-1.0.0.apk",
                    "apk_size": 18200000, # 18.2MB
                    "release_notes": "Initial release of Grievance Portal for android.",
                    "min_sdk_version": "23",
                    "permissions": ["INTERNET", "WRITE_EXTERNAL_STORAGE", "CAMERA"],
                    "sha256": "8f377f2a1a8c3d9df65961d70e4c6e3b5e36e4b8737f2a1a8c3d9df65961d7a"
                }
            }
        ]

        for app_data in apps_to_seed:
            slug = slugify(app_data["name"])
            q = select(App).where(App.slug == slug)
            res = await db.execute(q)
            app = res.scalar_one_or_none()
            if not app:
                category = db_categories[app_data["category"]]
                app = App(
                    name=app_data["name"],
                    slug=slug,
                    package_name=app_data["package_name"],
                    developer=app_data["developer"],
                    description=app_data["description"],
                    logo_url=app_data["logo_url"],
                    screenshots=app_data["screenshots"],
                    category_id=category.id,
                    is_active=True,
                    created_by=admin_user.id
                )
                db.add(app)
                await db.flush()
                logger.info(f"Created Application: {app.name}")

                # Create version
                v_data = app_data["version"]
                version = AppVersion(
                    app_id=app.id,
                    version_code=v_data["version_code"],
                    version_name=v_data["version_name"],
                    apk_url=v_data["apk_url"],
                    apk_size=v_data["apk_size"],
                    release_notes=v_data["release_notes"],
                    min_sdk_version=v_data["min_sdk_version"],
                    permissions=v_data["permissions"],
                    sha256=v_data["sha256"],
                    is_active=True,
                    created_by=admin_user.id
                )
                db.add(version)
                await db.flush()
                logger.info(f"Created Version {v_data['version_name']} for {app.name}")

        await db.commit()
        logger.info("Database seeding successfully completed!")


if __name__ == "__main__":
    asyncio.run(seed_data())
