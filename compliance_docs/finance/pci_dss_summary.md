# PCI DSS v4.0: summary of selected requirements

Plain-English summary for PerenicAI demonstrations. Not the official text of
the Payment Card Industry Data Security Standard, and not legal advice. PAN
means primary account number (the card number). SAD means sensitive
authentication data, such as the card verification code (CVV/CVC).

## Requirement 3.2.1 Keep stored account data to a minimum

Only store account data that is needed, only for as long as it is needed, and
securely delete it afterwards.

## Requirement 3.3.1 Do not keep sensitive authentication data after authorisation

SAD must not be kept after a payment is authorised, even if it is encrypted.
This includes the card verification code (3.3.1.2).

## Requirement 3.4.1 Mask the PAN when it is displayed

When a card number is shown, show at most the first six and last four digits,
unless a person has a documented business need to see more.

## Requirement 3.5.1 Make the PAN unreadable wherever it is stored

A stored PAN must be made unreadable, for example with strong one-way hashing,
truncation, tokenisation or strong encryption. This applies wherever it is
stored, including in logs.

## Requirement 4.2.1 Strong cryptography in transit

Use strong cryptography to protect the PAN while it is sent over open, public
networks.

## Requirement 6.2.4 Prevent common software attacks

Software engineering techniques must prevent or reduce common attacks, such as
injection attacks and attacks on data and data structures.

## Requirement 8.6.2 No hard-coded passwords for application and system accounts

Passwords or passphrases for application and system accounts that can be used
for interactive login must not be hard-coded in scripts, configuration files
or custom source code.

## Requirement 10.2.1 Audit logs

Audit logs must be enabled and active for all system components and for
cardholder data.
