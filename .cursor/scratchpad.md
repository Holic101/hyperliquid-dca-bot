# Hyperliquid DCA Bot: Codebase Cleanup Plan

## 1. Background and Motivation

The user wants to prepare the Hyperliquid DCA Bot codebase for deployment to a GitHub repository. The goal is to create a clean, professional, and secure project structure by removing unnecessary files, such as one-off test scripts, debugging utilities, and runtime-generated data. This ensures that the repository only contains essential code, configuration examples, and documentation, making it easier for others (or the user in the future) to understand, set up, and contribute to the project.

## 2. Key Challenges and Analysis

The main challenge is to correctly identify and remove files that are not essential for the final application without accidentally deleting critical logic or configuration.

-   **Distinguishing Test/Debug vs. Utility Scripts:** We need to differentiate between scripts created for one-time debugging (`diagnose_*.py`, `test_*.py`) and scripts that are part of the core functionality or deployment process (`check_and_trade.py`, `setup_cron.sh`).
-   **Handling Runtime Data:** Files like `dca_history.json` and the contents of the `logs/` directory are generated during the bot's operation. They should not be committed to the repository. The correct approach is to use a `.gitignore` file to exclude them.
-   **Configuration Files:** The project uses `dca_config.json`. We must ensure a clean, example version of this file is available for new setups, while the user's actual configuration is kept private and not committed.

## 3. High-level Task Breakdown

The cleanup process will be executed in the following steps. Each step must be completed and verified before proceeding to the next.

1.  **Create `.gitignore` File:**
    -   **Description:** Create a comprehensive `.gitignore` file to exclude runtime data, environment-specific files, and system files from version control.
    -   **Success Criteria:** The `.gitignore` file is created and contains patterns for `__pycache__/`, `logs/`, `*.json` (with an exception for `dca_config.example.json`), and `.env`.

2.  **Remove Obsolete Scripts:**
    -   **Description:** Delete all one-off debugging and testing scripts that are no longer needed for the final application.
    -   **Success Criteria:** The following files are deleted from the project directory:
        -   `diagnose_asset_id.py`
        -   `diagnose_margin.py`
        -   `diagnose_price_tick.py`
        -   `test_dca_execution.py`
        -   `test_spot_order.py`
        -   `test_spot_order_v2.py`

3.  **Standardize Configuration and Data Files:**
    -   **Description:** Rename the live `dca_config.json` and `dca_history.json` files to serve as examples, and ensure the live data files are untracked.
    -   **Success Criteria:**
        -   `dca_config.json` is renamed to `dca_config.example.json`.
        -   `dca_history.json` is deleted (as it will be ignored by git).
        -   The main application code (`hyperliquid_dca_bot.py` and `check_and_trade.py`) is updated to look for `dca_config.json`, which users will create from the new example file.

4.  **Final Code Review and Verification:**
    -   **Description:** Perform a final check to ensure the application still runs correctly after the cleanup.
    -   **Success Criteria:** The user confirms that the Streamlit app (`hyperliquid_dca_bot.py`) and the trading script (`check_and_trade.py`) can be executed without errors.

## 4. Project Status Board

-   [x] **Task 1:** Create `.gitignore` File - **COMPLETED**
-   [x] **Task 2:** Remove Obsolete Scripts - **COMPLETED**
-   [x] **Task 3:** Standardize Configuration and Data Files - **COMPLETED**
-   [x] **Task 4:** Final Code Review and Verification - **COMPLETED**

## 5. Executor's Feedback or Assistance Requests

**All cleanup tasks have been successfully completed.**

- A `.gitignore` file has been created to exclude unnecessary files from the repository.
- All temporary and one-off scripts (`diagnose_*.py`, `test_*.py`) have been deleted.
- The configuration file `dca_config.json` has been renamed to `dca_config.example.json` to serve as a template.
- The application code has been verified to work with the new file structure.

The codebase is now clean and ready for deployment to GitHub.

## 6. Lessons

- It is important to have a clear plan before modifying the codebase, especially when deleting files.
- Using a `.gitignore` file is crucial for keeping the repository clean and secure by excluding runtime data, environment-specific files, and sensitive information.
- Standardizing configuration files (e.g., using `*.example.json`) is a best practice that helps new users set up the project correctly. 