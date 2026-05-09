import asyncio
import asyncpg
import sys

async def test():
    dsn = "postgresql://neondb_owner:npg_uDYhfcpiy8w1@ep-bitter-forest-aoc1v14g-pooler.c-2.ap-southeast-1.aws.neon.tech/HireBase?sslmode=require"
    try:
        print(f"Connecting to {dsn}...")
        conn = await asyncpg.connect(dsn)
        print("Successfully connected!")
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test())
