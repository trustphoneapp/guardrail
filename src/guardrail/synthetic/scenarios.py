from datetime import datetime, timedelta
from decimal import Decimal

from guardrail.models import Transaction


def _txn(account_id, minutes_ago, amount, merchant, mcc, channel="card_not_present"):
    return Transaction(
        account_id=account_id,
        txn_id=f"{merchant.lower().replace(' ', '-')}-{minutes_ago}",
        ts=datetime.utcnow() - timedelta(minutes=minutes_ago),
        amount=Decimal(str(amount)),
        merchant_name=merchant,
        mcc=mcc,
        channel=channel,
    )


SCENARIOS = {
    "quiet_day": {
        "description": "Ordinary groceries + pharmacy — no signal should fire.",
        "transactions": [
            _txn("acct-1", 400, 42.10, "Safeway", "5411"),
            _txn("acct-1", 200, 18.75, "CVS Pharmacy", "5912"),
        ],
    },
    "grandparent_scam": {
        "description": "Three same-day gift-card purchases after a claimed emergency call.",
        "transactions": [
            _txn("acct-1", 180, 500, "Target GiftCard", "5411"),
            _txn("acct-1", 120, 500, "CVS GiftCard", "5912"),
            _txn("acct-1", 60, 500, "Walgreens GiftCard", "5912"),
        ],
    },
    "romance_wire": {
        "description": "A single large wire to a new, never-seen payee.",
        "transactions": [_txn("acct-1", 30, 4200, "Western Union", "4829", channel="wire")],
    },
    "tech_support": {
        "description": "Remote-access software purchase followed by an ATM withdrawal spike.",
        "transactions": [
            _txn("acct-1", 200, 299, "GeekSquad Remote", "7379"),
            _txn("acct-1", 90, 800, "ATM Withdrawal", "6011", channel="atm"),
        ],
    },
    "irs_scam": {
        "description": "Urgent same-hour gift-card burst, round dollar amounts.",
        "transactions": [
            _txn("acct-1", 45, 300, "Best Buy GiftCard", "5732"),
            _txn("acct-1", 30, 300, "Apple GiftCard", "5732"),
        ],
    },
    "quiet_day_second_elder": {
        # Same pipeline, different account_id/actor_id -- demonstrates
        # run_pipeline is already per-account parameterized, not a rebuild.
        # Not a multi-elder feature (no Elder model, no auth, no UI switcher
        # -- that was explicitly scoped out); this is one more fixture proving
        # the existing code already generalizes.
        "description": "A second elder's ordinary day, on a separate account_id -- no signal should fire.",
        "transactions": [
            _txn("acct-2", 500, 64.20, "Trader Joe's", "5411"),
            _txn("acct-2", 300, 22.00, "Walgreens Pharmacy", "5912"),
        ],
    },
}

# ponytail: 5 scenarios ship here, covering the demo's flagged + quiet paths. The
# architecture spec calls for 15-20 for fuller coverage — add entries following the
# same _txn() shape when the demo script needs a specific new pattern, not before.
