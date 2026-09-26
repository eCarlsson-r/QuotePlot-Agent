# QuotePlot Agent demo script

This is a 3–4 minute walkthrough for the Indonesia Web3 Hackathon. Rehearse it only after the live backend origin and Sepolia RPC are configured; the September 26, 2026 smoke check found both absent from the Vercel runtime config.

## Before recording

- Configure Vercel `QUOTE_PLOT_BACKEND_ORIGIN` and `QUOTE_PLOT_SEPOLIA_RPC_URL`; set backend `FRONTEND_URL` to `https://quote-plot-agent.vercel.app`.
- Rotate any RPC key that has appeared in pasted browser logs, update the Vercel RPC variable, and restrict the replacement key to the production origin.
- Check that the backend responds at `/docs`, `/api/market/tickers`, and `/api/agent/brightdata-status`, and that `/ws/thoughts` connects.
- Confirm the database has current market rows and at least one active Ethereum `TokenMap` entry for the demonstration symbol.
- Confirm the RPC provider allows the Vercel origin and that Sepolia factory ENS resolution succeeds. Use a wallet on chain ID `11155111` only if showing the token-management screen.
- Clear stale filters in both panels. Creation-event searches default to a recent 100,000-block window; use a valid range and click **Search events**.
- Close browser developer tools and hide credentials, API keys, private keys, and personal account details from the recording.

## Walkthrough and narration

### 0:00–0:30 — Introduce the problem

**Show:** QuotePlot Agent and the market panel.

**Say:** “Token research is spread across price data, model outputs, web sources, and blockchain explorers. QuotePlot Agent brings those signals into one investigation and keeps the evidence visible alongside Lucy's explanation.”

### 0:30–1:45 — Run a Lucy investigation

**Show:** Ask Lucy: “Investigate `<configured symbol>` and include the Ethereum token metadata and evidence you can verify.” Use a symbol confirmed in the deployed database's `TokenMap` and market history.

**Say:** “Lucy first gathers deterministic evidence. Market history and the local model come from the backend. Optional web sources may be available or unavailable. For chain metadata, the backend resolves the symbol through an active Ethereum token mapping and reads the mapped contract over JSON-RPC; it does not guess an address.”

**Show:** The response and evidence rows. Identify the actual status of each source on screen. Do not describe unavailable evidence as a negative signal.

### 1:45–2:30 — Explain the investigation boundary

**Show:** On-chain evidence details and the token-management area.

**Say:** “Gemini narrates the collected evidence when it is available. If narration is unavailable, Lucy returns a deterministic summary. The investigation is read-only: it does not sign, trade, or move assets. Wallet-based token-management actions are separate and require the user's Sepolia wallet approval.”

### 2:30–3:15 — Show Sepolia activity (only if verified)

**Show:** The connected Sepolia wallet, contract inventory, and matching creation event. Keep the walkthrough read-only unless the user intentionally wants to demonstrate a test transaction.

**Say:** “The token factory view uses the Sepolia ENS name `seed-token-factory.eth`. These rows are shown only when the RPC, factory deployment, and ENS record are configured. The event search stays within RPC block-range limits and shows its effective block range.”

If the wallet, factory, ENS record, or event query has not been verified, skip this segment and state that the hosted chain integration is not configured yet.

### 3:15–3:45 — Close with architecture

**Show:** Evidence panel and Lucy response together.

**Say:** “The backend handles evidence collection and deterministic fallback; Gemini provides the narration. This separation lets the user inspect what was available, what could not be retrieved, and which on-chain address was resolved through the project mapping.”

## Recording and release checks

- Record the actual deployed app after completing the preflight checks; do not splice in fabricated or stale evidence.
- Keep the recording concise, readable, and free of browser console errors. Show provider failures as unavailable rather than hiding or misrepresenting them.
- Publish the video as public or unlisted according to the submission portal's current instructions, then verify the URL in a signed-out browser.
- Add the live demo and video links to `docs/SUBMISSION.md` only after opening them successfully from a separate session.
- The official event listing states that submission runs September 1–30, 2026 and allows submitting a pitch deck before the project is fully complete. No submission or video upload has been made from this repository.
