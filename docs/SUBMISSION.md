# Demo and submission readiness

This checklist records what can be prepared from the repository. It does not claim that a hosted deployment or hackathon submission has been completed.

## Validation snapshot (September 26, 2026)

- Backend: all 18 deterministic `unittest` cases pass; `compileall` passes. The Arrow library emitted non-fatal host `sysctl` permission warnings.
- Frontend: TypeScript application type-check passes; Angular/Vitest reports 1 test passing. `npm run build` exits 134 locally while the esbuild service reports `all goroutines are asleep - deadlock` during bundle generation.
- Contracts: all 5 Hardhat tests pass against checked-in compiled artifacts with `npx hardhat test --no-compile`. Fresh `npx hardhat compile` timed out acquiring the global compiler-download-list mutex after 60 seconds.
- Live frontend: `https://quote-plot-agent.vercel.app/` loads. Its current browser config has no backend origin or custom Sepolia RPC, so Lucy/market API and wallet/chain flows are not end-to-end verified. The live panel shows empty inventory and no matching creation events without a connected wallet/configured RPC.
- Live backend / Sepolia: not verified from this checkout. The project owner reports backend deployment success, but the public backend origin, environment health, DB contents, deployed factory address, Sepolia ENS resolution, and wallet transaction path are not available here.

Treat a production Angular build, fresh Solidity compilation, configured backend/RPC origins, and live deployment checks as release gates before submission.

## Candidate track and project summary

The event listing currently offers **AI Agents**, **Finance & Commerce**, and **Consumer Apps** tracks and sets the final submission deadline to **September 30, 2026**. It says a pitch deck may be submitted first and the project details improved through the submission period. Check the organizer's [event page](https://luma.com/pcc699dv) and [submission portal](https://indonesiaweb3hack.xyz) before entering the final details.

- Candidate track: **AI Agents**. Lucy can select and call read-only tools to collect on-chain evidence through Ethereum JSON-RPC. Describe this accurately as user-directed investigation; the agent does not autonomously sign transactions or move assets. If the judging rubric requires autonomous write actions on-chain, confirm track fit with the organizers rather than implying the app performs them.
- One-line summary: **QuotePlot Agent is a Web3 market-investigation app where Lucy combines market data, model output, web context, and mapped Ethereum token evidence into a sourced token investigation.**
- Problem: Token research is split across price feeds, model outputs, web sources, and explorers, making it hard to see which claims are actually supported.
- Approach: Lucy routes a user question into deterministic evidence gathering, resolves on-chain symbols only through active `TokenMap` records, and narrates collected evidence with Gemini when available.
- Safety boundary: The investigation path is read-only. Wallet token creation, minting, and ownership actions are separate user-confirmed Sepolia transactions.
- Tech: Angular, FastAPI/Python, Gemini, Bright Data, SQLAlchemy, Ethereum JSON-RPC, Solidity, and Hardhat.

### Pitch deck outline

1. **Problem:** Evidence about a token is scattered across market, model, web, and chain sources.
2. **Product:** QuotePlot Agent and Lucy's investigation interface.
3. **Investigation flow:** User question → deterministic source retrieval → evidence statuses → Gemini narration or deterministic fallback.
4. **Web3 proof path:** Active `TokenMap` → JSON-RPC token metadata; show a verified Sepolia factory only after its address and ENS record are checked.
5. **Trust and limits:** Read-only investigation; missing providers are marked unavailable/insufficient; no claims of autonomous trading.
6. **Demo and roadmap:** Use only the live URL, screenshots, and addresses that have passed the checklist below; identify remaining integration work plainly.

## Before a live demo

- [ ] Configure a reachable database, initialize its schema, and confirm it contains recent price rows plus active `TokenMap` rows. At least one demonstrated ERC-20 must map to an Ethereum contract address.
- [ ] Configure backend `GEMINI_API_KEY`, `ETH_RPC_URL`, and `FRONTEND_URL`. Configure Bright Data credentials if live web/social context will be shown. Missing optional providers should appear as unavailable evidence.
- [ ] Confirm the deployed backend's public origin and verify `/docs`, `/api/market/tickers`, `/api/agent/brightdata-status`, and WebSocket `/ws/thoughts` from the hosted origin.
- [ ] Build/deploy Angular with `QUOTE_PLOT_BACKEND_ORIGIN` and `QUOTE_PLOT_SEPOLIA_RPC_URL`; confirm backend CORS and RPC provider origin restrictions.
- [ ] Deploy the contracts to Sepolia using a funded deployer, record the printed addresses, and configure Sepolia `seed-token-factory.eth` to the factory address.
- [ ] Connect a Sepolia wallet (chain ID `11155111`) and confirm the app reports the expected wallet/network and factory. Keep the deployer private key out of browser/frontend configuration.
- [ ] Run the backend, frontend, and contract validation commands in the README against the final commit. Recheck credentials and browser console/network errors on the actual demo origin.

## Suggested 3–4 minute walkthrough

1. Open the live Angular app and show Lucy, market context, and the Sepolia wallet connection status.
2. Ask Lucy: **“Investigate DAI, including its Ethereum contract metadata and what evidence you can verify.”** Use a token symbol that has a live, active Ethereum `TokenMap` entry and recent market history in the deployed database; substitute that symbol if DAI is not configured.
3. Show the answer and the evidence rows. Call out which sources are available and which are unavailable or insufficient. Confirm the on-chain address and token metadata came from the configured mapping and RPC response.
4. Connect the Sepolia wallet and show the factory/token-management UI. If demonstrating a write action, use test funds and explicitly confirm the wallet transaction. Otherwise keep the walkthrough read-only.
5. Close with the architecture: evidence gathering and deterministic fallback happen in the backend; Gemini supplies narration; the on-chain investigator performs reads and does not trade.

If Gemini or a provider is unavailable, show the collected fallback/evidence and state that source as unavailable. Do not present absent data as a market signal. Do not fabricate successful live addresses or deployment checks.

## Submission package to fill with verified values

- Project name: QuotePlot Agent
- Track/category: candidate **AI Agents**; confirm the track fit and current portal fields against the organizer information before submitting.
- One-line description: Lucy combines market data, model output, web context, and verified Ethereum token metadata into an evidence-backed investigation.
- Repository: `https://github.com/eCarlsson-r/QuotePlot-Agent`
- Live demo: **add only after the deployed URL has been tested**
- Demo video: **record after the final live walkthrough; add URL after upload**
- Sepolia factory/token addresses: **add after deployment and verify on a Sepolia explorer**
- Team/member details: **enter the actual participant information in the official submission form**

Before sending the form, verify the deadline and required fields on the official event site, check that repository/demo/video links are publicly accessible, and ensure the video shows the implemented flow. Submission is an external action and has not been performed from this workspace.
