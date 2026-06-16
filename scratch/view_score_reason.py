import asyncio
import json
from sqlalchemy import text
from app.core.database.base import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT final_score, risk_level, red_flags, explanation FROM candidate_scores WHERE application_id = 698")
        )
        row = result.fetchone()
        if not row:
            print("No candidate score found for application 698.")
            # Let's check if there are other scores
            all_scores = await session.execute(text("SELECT application_id, final_score, risk_level FROM candidate_scores ORDER BY id DESC LIMIT 5"))
            print("--- Recent scores ---")
            for r in all_scores.fetchall():
                print(r)
            return
            
        print("=== CANDIDATE SCORE FOR APP 698 ===")
        print(f"Final Score: {row[0]}")
        print(f"Risk Level: {row[1]}")
        try:
            print(f"Red Flags: {json.dumps(row[2], indent=2) if isinstance(row[2], (dict, list)) else row[2]}")
        except Exception as e:
            print(f"Red Flags raw: {row[2]} (Error formatting: {e})")
        print("\nExplanation:")
        print(row[3])

if __name__ == "__main__":
    asyncio.run(main())
