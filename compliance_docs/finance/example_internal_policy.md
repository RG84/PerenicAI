# Example internal engineering policy: finance

An example of the kind of internal policy PAT Compliance can check against.
Replace it with your organisation's real policies.

## FIN-1 Money uses Decimal

All monetary amounts must use `decimal.Decimal`, never `float`. Round to the
currency's minor unit (2 decimal places for USD) with `ROUND_HALF_EVEN`.

## FIN-2 Payments must be idempotent

Every request that charges, refunds or transfers money must carry an
idempotency key, so a retried request can never move money twice.

## FIN-3 Audit trail for money movement

Every change to an account balance must write an audit record with the
amount, before and after balances, who made the change and when.

## SEC-1 Card data handling

Card numbers must be tokenised by the payment provider. Our systems must never
log, print or store a full card number or a CVV.
