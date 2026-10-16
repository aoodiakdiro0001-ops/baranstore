# 🏪 Baran Store Bot — متجر باران على تيليجرام

Designed & built by **Baran Avisat** (Professional Programmer).
📧 baranavisat@gmail.com · 📞 +90 531 326 37 22

Storefront bot for all Baran services: catalog, guided orders, tickets,
crypto payments (USDT/BTC + `/paid` TXID), admin notifications.

## Run (24/7 on your Mac, no hosting)

```bash
cp store/.env.example store/.env   # NEW bot token + ADMIN_ID (never commit)
python3 store/bot.py
# launchd: same pattern as baranexcel/cleaner (see its README)
```

## Flow
`/start` → catalog buttons → order (service → details/file → تم) →
ticket `T-0001` → admin gets user + details + forwarded file →
user pays → `/paid TXID` → admin delivers.
