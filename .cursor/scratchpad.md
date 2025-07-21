# Scratchpad: Multi-Asset Support Implementation Plan

## Background and Motivation
The current bot is designed to trade a single asset (Bitcoin). To increase its utility and allow for portfolio diversification, we need to refactor the architecture to support trading multiple assets simultaneously, each with its own independent DCA strategy. This plan details the necessary changes to the configuration, core logic, state management, and user interface.

---

## High-level Task Breakdown

This plan is broken down into four main phases:
1.  **Configuration Rearchitecture:** Change the structure of the configuration file and data classes to accommodate multiple assets.
2.  **Core Logic Refactoring:** Adapt the trading and data-fetching logic to operate on a per-asset basis.
3.  **State Management Update:** Modify the trade history to be asset-aware.
4.  **Dashboard Enhancement:** Update the Streamlit UI to display data for multiple assets.

---

## Project Status Board

### Phase 1: Configuration Rearchitecture
- [ ] **Task 1.1:** Redesign `dca_config.json` to support a list of assets.
- [ ] **Task 1.2:** Create new Python dataclasses (`AssetConfig`, `GlobalConfig`, `DCAConfig`) to match the new structure.
- [ ] **Task 1.3:** Update the `load_config` and `save_config` functions to handle the new format.

### Phase 2: Core Logic Refactoring
- [ ] **Task 2.1:** Create a new main execution loop (`run_all_strategies`) that iterates over each asset configuration.
- [ ] **Task 2.2:** Modify `execute_dca_trade` to `execute_trade_for_asset`, which accepts a specific `AssetConfig`.
- [ ] **Task 2.3:** Update data-fetching methods (`get_historical_prices`, `get_asset_price`) to be generic and accept an asset symbol.
- [ ] **Task 2.4:** Make the `should_execute_trade` check asset-specific by tracking the last trade time for each asset.

### Phase 3: State Management Update
- [ ] **Task 3.1:** Update the `TradeRecord` dataclass to include an `asset` field.
- [ ] **Task 3.2:** Modify `load_history` and `save_history` to handle the new `TradeRecord` format.

### Phase 4: Dashboard Enhancement
- [ ] **Task 4.1:** Add a dropdown selector to the Streamlit UI to choose which asset's data to display.
- [ ] **Task 4.2:** Update all charts, metrics, and tables to filter and display data based on the selected asset.
- [ ] **Task 4.3:** Create a portfolio-level summary view that aggregates key metrics from all assets.

---

## Detailed Implementation Steps

### Phase 1: Configuration Rearchitecture

**Task 1.1: Redesign `dca_config.json`**
*   **Action:** The current flat JSON structure will be changed to a nested one. There will be a `global_settings` object for the private key and wallet address, and an `assets` list, where each item is an object containing the full DCA strategy for that asset (e.g., symbol, amount, frequency, volatility thresholds).
*   **Success Criteria:** A new `dca_config.example.json` file is created that clearly shows the new structure with at least two example assets (e.g., BTC and ETH).

**Task 1.2: Create new Dataclasses**
*   **Action:** In `hyperliquid_dca_bot.py`, replace the existing `DCAConfig` with three new dataclasses:
    1.  `AssetConfig`: Holds all settings for a single asset.
    2.  `GlobalConfig`: Holds the `private_key` and `wallet_address`.
    3.  `DCAConfig`: The main config object, containing a `global_settings` field (`GlobalConfig`) and an `assets` field (a list of `AssetConfig`).
*   **Success Criteria:** The new dataclasses are implemented and correctly represent the new JSON structure.

**Task 1.3: Update Config Functions**
*   **Action:** Rewrite the `load_config` and `save_config` functions to correctly parse the new nested JSON into the new dataclass structure and serialize it back.
*   **Success Criteria:** The bot can successfully load and save the new multi-asset configuration without errors.

---

## Executor's Feedback or Assistance Requests

**CRITICAL ISSUE FIXED (2025-07-21):** 
- **Problem**: The bot was failing with `KeyError: 'BTC/USDC'` when trying to execute trades
- **Root Cause**: Incorrect symbol usage in Hyperliquid API calls:
  - `l2_snapshot()` was being called with "BTC" which is not a valid symbol
  - `all_mids()` was being called with "BTC" instead of "UBTC"
  - Spot balance lookup was using "BTC" instead of "UBTC"
- **Solution**: Updated the code to use correct Hyperliquid API symbols:
  - Use `all_mids()` instead of `l2_snapshot()` for price data
  - Use "UBTC" for Bitcoin-related API calls
  - Use "UBTC/USDC" for spot trading orders
- **Files Modified**: `hyperliquid_dca_bot.py` - updated `get_btc_price()` and `calc_unrealized_pnl()` methods

**Current Status**: The bot should now be able to execute trades without the KeyError. Ready for testing.

---

## Lessons

**Hyperliquid API Symbol Usage (2025-07-21):**
- For price data: Use `all_mids()` method with "UBTC" symbol
- For spot trading: Use "UBTC/USDC" as the trading pair
- For balance checks: Look for "UBTC" in spot balances
- Do NOT use "BTC" or "BTC/USDC" as these are not valid symbols in Hyperliquid's API
- The `l2_snapshot()` method may not be the correct approach for getting current prices in this context 