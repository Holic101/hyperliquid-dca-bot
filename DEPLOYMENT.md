# Hyperliquid DCA Bot VPS Deployment Guide

This guide provides step-by-step instructions to deploy the Hyperliquid DCA Bot on a Linux Virtual Private Server (VPS), for example, one running Ubuntu 22.04.

This setup ensures your Streamlit dashboard runs continuously and your automated trading script executes reliably on schedule.

---

## Phase 1: Server Preparation

First, connect to your VPS via SSH and ensure the system is up-to-date and has the necessary software.

### 1. Update Your Server
Run the following command to update your system's package lists and upgrade existing packages:
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Required Software
Install Python, its package manager (`pip`), the virtual environment tool (`venv`), and Git:
```bash
sudo apt install python3 python3-pip python3-venv git -y
```

---

## Phase 2: Application Deployment & Configuration

Now, you will clone the project from your GitHub repository and set it up.

### 1. Clone Your Repository
Clone the project code from your GitHub repository.
```bash
git clone https://github.com/Holic101/hyperliquid-dca-bot.git
```
This will create a `hyperliquid-dca-bot` directory.

### 2. Set Up the Python Virtual Environment
Navigate into your project directory and create an isolated Python environment. This is a best practice to avoid dependency conflicts.
```bash
cd hyperliquid-dca-bot
python3 -m venv .venv
```
Activate the environment:
```bash
source .venv/bin/activate
```
You should see `(.venv)` at the beginning of your command prompt, indicating the environment is active.

### 3. Install Dependencies
Install all the required Python packages using the `requirements.txt` file:
```bash
pip install -r requirements.txt
```

### 4. Configure Your Secrets
Create a `.env` file to securely store your private keys and passwords. This file is ignored by Git and will not be public.

Create the file using a text editor like `nano`:
```bash
nano .env
```
Paste the following content into the editor, replacing the placeholder values with your actual secrets:
```env
# Your private key for the Hyperliquid wallet (must start with 0x)
HYPERLIQUID_PRIVATE_KEY="your_private_key_here"

# Your public wallet address
HYPERLIQUID_WALLET_ADDRESS="your_wallet_address_here"

# A strong, unique password to protect your Streamlit dashboard
DCA_BOT_PASSWORD="a_strong_password_for_the_dashboard"
```
To save and exit in `nano`, press `Ctrl+X`, then `Y`, then `Enter`.

### 5. Create Your Local Config
Create a `dca_config.json` file from the provided example:
```bash
cp dca_config.example.json dca_config.json
```
You can edit this file (`nano dca_config.json`) if you need to change your trading strategy, but the defaults will work with the secrets you just provided.

---

## Phase 3: Automation & Process Management

This phase ensures your Streamlit app runs 24/7 and your trading script runs on schedule.

### 1. Set Up a `systemd` Service for the Streamlit App
`systemd` is a modern system for managing processes in Linux. This will ensure your dashboard starts automatically on boot and restarts if it ever crashes.

Create a new service file:
```bash
sudo nano /etc/systemd/system/dca-bot.service
```
Paste the following service definition into the file. **You must replace `your_user` with your actual username on the VPS.**

```ini
[Unit]
Description=Hyperliquid DCA Bot Streamlit Service
After=network.target

[Service]
# Replace 'your_user' with your actual username
User=your_user
Group=your_user

# Replace 'your_user' with your actual username in the path
WorkingDirectory=/home/your_user/hyperliquid-dca-bot
ExecStart=/home/your_user/hyperliquid-dca-bot/.venv/bin/streamlit run /home/your_user/hyperliquid-dca-bot/hyperliquid_dca_bot.py --server.port 8501 --server.headless true

Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```
Save and exit (`Ctrl+X`, `Y`, `Enter`).

### 2. Set Up a `cron` Job for Automated Trading
This will run your `check_and_trade.py` script on a schedule, replacing the need for GitHub Actions.

Open your user's crontab for editing:
```bash
crontab -e
```
You may be prompted to choose an editor; `nano` is a good choice.

Add the following line to the bottom of the file. This example schedules the job to run every Monday at 9:00 AM UTC. **Remember to replace `your_user` with your actual username.**

```cron
# Run the Hyperliquid DCA bot script every Monday at 9:00 AM UTC
0 9 * * 1 /home/your_user/hyperliquid-dca-bot/.venv/bin/python /home/your_user/hyperliquid-dca-bot/check_and_trade.py >> /home/your_user/hyperliquid-dca-bot/logs/cron.log 2>&1
```
This command does three things:
1.  Specifies the schedule (`0 9 * * 1`).
2.  Provides the full path to the Python interpreter in your virtual environment and the script to run.
3.  Redirects all output and errors to a log file (`cron.log`) for easy debugging.

Save and exit the crontab editor.

---

## Phase 4: Finalization

Let's start the services and open the firewall.

### 1. Start and Enable the Streamlit Service
Tell `systemd` to recognize and run your new service:
```bash
# Reload systemd to recognize the new file
sudo systemctl daemon-reload

# Start the service immediately
sudo systemctl start dca-bot

# Enable the service to start automatically on boot
sudo systemctl enable dca-bot
```

### 2. Check the Service Status
Verify that the service is running correctly:
```bash
sudo systemctl status dca-bot
```
You should see a green "active (running)" status. Press `Q` to exit the status view.

### 3. Configure Firewall (If Applicable)
If you are using a firewall like `ufw` (Uncomplicated Firewall), you need to allow traffic on port 8501 for Streamlit.
```bash
sudo ufw allow 8501/tcp
sudo ufw reload
```

### 4. Access Your Dashboard
You should now be able to access your Streamlit dashboard in your web browser at:
`http://your_vps_ip:8501`

---

Your deployment is complete! Your dashboard is live, and your automated trading script is scheduled to run. 