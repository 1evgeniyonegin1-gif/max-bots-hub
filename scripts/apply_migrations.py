"""
Скрипт для применения SQL миграций
Запуск: python scripts/apply_migrations.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from shared.database import engine


async def apply_migration(migration_file: Path):
    """Применить одну миграцию"""
    print(f"📦 Applying: {migration_file.name}")

    sql = migration_file.read_text(encoding='utf-8')

    # Разбиваем на отдельные команды (по ;)
    # Игнорируем комментарии и пустые строки
    statements = []
    current = []

    for line in sql.split('\n'):
        stripped = line.strip()

        # Пропускаем комментарии и секции ROLLBACK
        if stripped.startswith('--'):
            if 'ROLLBACK' in stripped:
                break  # Не выполняем rollback секцию
            continue

        current.append(line)

        if stripped.endswith(';'):
            stmt = '\n'.join(current).strip()
            if stmt and stmt != ';':
                statements.append(stmt)
            current = []

    async with engine.begin() as conn:
        for i, stmt in enumerate(statements, 1):
            try:
                await conn.execute(text(stmt))
                print(f"   ✅ Statement {i}/{len(statements)} OK")
            except Exception as e:
                error_msg = str(e)
                # Игнорируем ошибки "already exists"
                if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
                    print(f"   ⚠️  Statement {i}/{len(statements)} skipped (already exists)")
                else:
                    print(f"   ❌ Statement {i}/{len(statements)} FAILED: {error_msg}")
                    raise

    print(f"✅ Migration {migration_file.name} applied successfully!\n")


async def main():
    """Применить все миграции по порядку"""
    migrations_dir = project_root / 'migrations' / 'versions'

    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        return

    # Получаем список миграций, сортируем по номеру
    migrations = sorted(migrations_dir.glob('*.sql'))

    if not migrations:
        print("📭 No migrations found")
        return

    print(f"🚀 Found {len(migrations)} migration(s)")
    print("=" * 50)

    for migration in migrations:
        await apply_migration(migration)

    print("=" * 50)
    print("🎉 All migrations applied successfully!")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("MAX BOTS HUB - Database Migrations")
    print("=" * 50 + "\n")

    asyncio.run(main())
