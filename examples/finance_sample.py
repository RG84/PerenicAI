"""A deliberately flawed payments file to try PAT Finance on.

Run:  python -m perenic review examples/finance_sample.py --industry finance
(The card number below is a public test number, not a real card.)
"""

import logging

logger = logging.getLogger(__name__)

STRIPE_API_KEY = "sk_test_do_not_commit"
TEST_CARD = "4111 1111 1111 1111"


def charge(card_number, amount: float):
    """Charge a card."""
    logger.info("Charging card %s", card_number)
    fee = 0.30
    total = amount + fee
    return total


def apply_refund(balance, refund_text):
    """Add a refund to an account balance."""
    refund = float(refund_text)
    return balance + refund
