from storage.db import SessionLocal
from storage. repository import deposit_credits

db = SessionLocal()
try:
    tx = deposit_credits(db, user_id=2, amount=50, description='Test deposit')
    print(f'Success!  Transaction ID: {tx.id}, Amount: {tx.amount}')
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()