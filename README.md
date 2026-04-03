# 🌊 ProxyForge

> **Async proxy tester with Telegram API support and multilingual interface**

- Language:**ENGLISH**/[RUSSIAN](README_RU.md)

## 📒 Description

`ProxyForge` is a powerful command-line tool for mass proxy server testing. Thanks to its asynchronous architecture, it can test hundreds of proxies simultaneously, automatically sorts them by type (SOCKS5, SOCKS4, HTTPS, HTTP), and identifies those suitable for Telegram.

## ✨ Features

- 🚀 **Asynchronous testing** — up to 50+ proxies simultaneously
- 🧩 **Two operation modes**:
  - `Standard` — general proxy functionality testing
  - `Telegram` — testing Telegram API and bot availability
- 🗂 **Smart sorting** — separates results by protocol (SOCKS5 → SOCKS4 → HTTPS → HTTP)
- 🌐 **Multilingual** — supports Russian and English (system auto-detection)
- 🤖 **Telegram Bot API integration** — checks if a proxy can work with your specific bot
- ⚙️ **Persistent settings** — configuration saved between sessions
- 📊 **Progress bar** — visual testing progress with `tqdm`

## 📦 Installation

1. **Clone the repository** (or download the project files):
   ```bash
   git clone https://github.com/username/ProxyForge.git
   cd ProxyForge
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Quick Start

Launch the main menu:
```bash
python proxy_launcher.py
```

The interactive menu will prompt you to select a mode, proxy file, and additional parameters.

### Example: Standard Mode

1. Create a `proxies.txt` file (one proxy per line):

   *The proxies.txt file is shown as an example. Create it yourself and add your proxies.*
   ```
   192.168.1.1:8080
   socks5://user:pass@192.168.1.2:1080
   https://192.168.1.3:3128
   ```
3. Run `proxy_launcher.py`, select `1` → `Standard Proxy Check`.
4. Get results: a list of working proxies in `working_proxies.txt`, sorted by type.

## 🛠 Command-Line Usage (CLI)

You can call scripts directly without the launcher.

### Standard Tester (`proxy_tester.py`)

```bash
python proxy_tester.py -i proxies.txt -o working.txt -t 10 -c 100 -l en
```

**Options:**
- `-i` — input file with proxies
- `-o` — output file for working proxies
- `-t` — timeout in seconds (default: 10)
- `-c` — number of concurrent checks (default: 50)
- `-l` — language (`en` or `ru`)

### Telegram Tester (`proxy_tester_telegram.py`)

```bash
python proxy_tester_telegram.py -i proxies.txt -b "YOUR_BOT_TOKEN" -c 30
```

**Additional option:**
- `-b` — your Telegram bot token for extended verification (the bot must exist)

## 📁 Project Structure

```bash
ProxyForge/
├── proxy_launcher.py          # Interactive menu
├── proxy_tester.py            # Core testing module
├── proxy_tester_telegram.py   # Telegram testing module
├── requirements.txt           # Dependencies
├── locales/                   # Language files
│   ├── __init__.py            # i18n module
│   ├── en.json                # English translations
│   └── ru.json                # Russian translations
├── config/                    # Settings
│   ├── __init__.py
│   └── settings.py            # Config management (save/load)
└── README.md
```

## 🧠 How It Works

1. **Proxy parsing** — file parsing supporting `IP:PORT`, `http://`, `socks5://` formats
2. **Type detection** — port 1080/9050 → `SOCKS5`, otherwise → `HTTP`
3. **Asynchronous testing** — using `aiohttp` and `aiohttp_socks` to send requests to test URLs (for Telegram — to `api.telegram.org`)
4. **Filtering and sorting** — only responsive proxies are saved, grouped by protocol
5. **Saving results** — to a file with headers and statistics

## 📝 Example Output File (`working_proxies.txt`)

```text
# ProxyForge - 2025-01-15 14:30:22
# Total checked: 15
# ==========================================================

# Working by type:
#   SOCKS5: 3
#   HTTPS: 5
#   HTTP: 2

# ========== SOCKS5 (3 pcs) ==========
socks5://45.76.145.11:1080
socks5://user:pass@103.152.108.16:1080

# ========== HTTPS (5 pcs) ==========
https://192.74.255.195:3128
https://23.88.5.24:8080
```

## ⚠️ Common Errors and Solutions

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'aiohttp'` | Install dependencies: `pip install -r requirements.txt` |
| `❌ File proxies.txt not found!` | Create a proxy file or specify the correct path with `-i` |
| `ProxyConnectionError` | Proxy is not responding — likely dead or requires authentication |
| `TimeoutError` | Increase timeout with `-t 15` or `-t 20` |

## 📄 License

[MIT](https://choosealicense.com/licenses/mit/)
