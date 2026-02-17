"""
Secure admin provisioning utility.

Creates or updates an admin account with a properly hashed password.

Usage examples:
  python -m app.create_admin --email admin@kabulsweets.com.au --full-name "Kabul Admin"
  python -m app.create_admin --email staff@kabulsweets.com.au --promote-existing --reset-password
"""

import argparse
import asyncio
import getpass
from typing import NoReturn

from sqlalchemy import func, select

from app.core.database import async_session_factory
from app.core.logging import get_logger, setup_logging
from app.core.security import hash_password
from app.models.user import User, UserRole

logger = get_logger("create_admin")


def _normalize_email(raw: str) -> str:
    return raw.strip().lower()


def _resolve_password(cli_password: str | None) -> str:
    if cli_password:
        password = cli_password.strip()
    else:
        first = getpass.getpass("Admin password: ").strip()
        second = getpass.getpass("Confirm password: ").strip()
        if first != second:
            raise ValueError("Passwords do not match.")
        password = first

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    return password


def _fail(message: str) -> NoReturn:
    raise SystemExit(f"❌ {message}")


async def _create_or_update_admin(args: argparse.Namespace) -> None:
    email = _normalize_email(args.email)
    full_name = (args.full_name or "").strip() or email.split("@")[0]
    phone = args.phone.strip() if args.phone else None
    password = _resolve_password(args.password)

    async with async_session_factory() as session:
        result = await session.execute(select(User).where(func.lower(User.email) == email))
        existing = result.scalar_one_or_none()

        if existing is None:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=full_name,
                phone=phone,
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            await session.commit()
            logger.info("Created admin account: %s", email)
            print(f"✅ Admin account created: {email}")
            return

        # Existing user path
        if existing.role != UserRole.ADMIN and not args.promote_existing:
            _fail(
                "User exists with non-admin role. Re-run with --promote-existing "
                "to explicitly promote this account."
            )

        existing.role = UserRole.ADMIN
        existing.is_active = True
        existing.is_verified = True

        if args.full_name:
            existing.full_name = full_name
        if args.phone is not None:
            existing.phone = phone

        if args.reset_password:
            existing.hashed_password = hash_password(password)
            logger.info("Reset password for admin account: %s", email)

        await session.commit()
        print(f"✅ Admin account updated: {email}")
        if args.reset_password:
            print("🔐 Password was reset with Argon2 hashing.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create/update an admin account safely (hashed password)."
    )
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--full-name", help="Full name")
    parser.add_argument("--phone", default=None, help="Phone number")
    parser.add_argument(
        "--password",
        help="Password (omit to enter securely via prompt)",
    )
    parser.add_argument(
        "--promote-existing",
        action="store_true",
        help="Allow promoting an existing non-admin user to admin",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Reset password for existing account",
    )
    return parser


def main() -> None:
    setup_logging()
    parser = _build_parser()
    args = parser.parse_args()
    try:
        asyncio.run(_create_or_update_admin(args))
    except ValueError as exc:
        _fail(str(exc))


if __name__ == "__main__":
    main()
