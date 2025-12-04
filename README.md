<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Coinbase-API-0052FF?style=for-the-badge&logo=coinbase&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Status-Active-success?style=for-the-badge" />
</p>

<h1 align="center">🤖 Crypto Trading Bot</h1>

<p align="center">
  <strong>An intelligent cryptocurrency trading bot with technical analysis, sentiment analysis, and machine learning capabilities.</strong>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-strategies">Strategies</a> •
  <a href="#-technical-details">Technical Details</a>
</p>

---

## 📋 Overview

This project is a fully autonomous cryptocurrency trading bot built in Python that connects to the Coinbase Advanced Trade API. It combines **technical analysis**, **sentiment analysis**, and **adaptive learning** to make intelligent trading decisions.

The bot features a "brain" system that remembers all trades, tracks performance metrics, adjusts its strategy based on outcomes, and implements risk management to protect capital.

![Alt Text]([path/to/image.jpg](https://ibb.co/hxcR4Qxs) "")
```
┌─────────────────────────────────────────────────────────────────────┐
│                        SMART TRADER v4                              │
├─────────────────────────────────────────────────────────────────────┤
│  📊 Technical Analysis    +    📰 Sentiment Analysis               │
│  (RSI, MACD, SMA, BB)         (Reddit, News, Fear & Greed)          │
│            │                            │                           │
│            └──────────┬─────────────────┘                           │
│                       ▼                                             │
│              🧠 Trading Brain                                      │
│         (Memory, Learning, Risk Mgmt)                               │
│                       │                                             │
│                       ▼                                             │
│              💹 Trade Execution                                     │
│            (Coinbase Advanced API)                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### 🔹 Technical Analysis Engine
- **RSI (Relative Strength Index)** — Identifies overbought/oversold conditions
- **MACD (Moving Average Convergence Divergence)** — Detects momentum shifts and crossovers
- **Simple Moving Averages (SMA-7, SMA-25)** — Determines trend direction
- **Bollinger Bands** — Identifies volatility and price extremes
- **Hourly candlestick data** — Real-time market analysis

### 🔹 Sentiment Analysis Module
- **Fear & Greed Index** — Market-wide sentiment indicator (0-100 scale)
- **Reddit Sentiment** — Scans r/bitcoin and r/cryptocurrency for bullish/bearish keywords
- **News Analysis** — Processes crypto news headlines for sentiment signals
- **Weighted Combination** — Merges all sources into actionable signals

### 🔹 Intelligent Trading Brain
- **Persistent Memory** — Remembers all trades across sessions (JSON storage)
- **Performance Tracking** — Calculates win rate, P/L, best/worst trades
- **Adaptive Thresholds** — Adjusts RSI/signal requirements based on performance
- **Risk Management** — Auto-stops after consecutive losses or drawdown limits
- **Human-like Reasoning** — Generates explanations for every decision

### 🔹 Multiple Trading Strategies
| Strategy | Risk Level | Description |
|----------|------------|-------------|
| DCA (Dollar Cost Average) | Low | Fixed purchases at regular intervals |
| Grid Trading | Medium | Buy/sell orders at price intervals |
| Momentum Trading | Medium-High | Technical indicator-based signals |
| Smart Accumulator v4 | Adaptive | Full AI with sentiment + learning |

---

## 🏗 Architecture

```
crypto-bot/
├── src/
│   ├── coinbase_client.py    # API connection & authentication
│   ├── trader.py             # Trade execution (buy/sell/orders)
│   ├── data_fetcher.py       # Historical data & technical indicators
│   ├── sentiment_analyzer.py # Reddit/News/Fear&Greed analysis
│   └── trading_brain.py      # Memory, learning, risk management
│
├── strategies/
│   ├── dca_strategy.py       # Dollar Cost Averaging bot
│   ├── grid_strategy.py      # Grid trading bot
│   ├── momentum_strategy.py  # Technical analysis bot
│   └── smart_trader_v4.py    # Full AI trading bot
│
├── .env                      # API keys (not tracked)
├── .env.example              # API key template
├── requirements.txt          # Python dependencies
└── README.md                 # Documentation
```

---

## 🛠 Installation

### Prerequisites
- Python 3.12 or higher
- Coinbase account with Advanced Trade API access
- USDC balance for trading

### Step 1: Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/crypto-trading-bot.git
cd crypto-trading-bot
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure API Keys

1. Go to [Coinbase Developer Platform](https://portal.cdp.coinbase.com/)
2. Create a new API Key with **Advanced Trade** permissions
3. Enable **View** and **Trade** scopes
4. Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

5. Edit `.env` with your credentials:

```env
COINBASE_API_KEY=organizations/your-org-id/apiKeys/your-key-id
COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----
YOUR_PRIVATE_KEY_HERE
-----END EC PRIVATE KEY-----
```

> ⚠️ **Important:** The private key must include the BEGIN/END lines and use actual line breaks.

### Step 4: Verify Connection
```bash
cd src
python coinbase_client.py
```

You should see:
```
============================================================
✅ CONNECTION SUCCESSFUL!
============================================================
💰 Your Balances:
   USDC: 30.75
============================================================
```

---

## 🚀 Usage

### Quick Trade Commands

```python
# Buy $10 of Bitcoin
from trader import buy_crypto
buy_crypto('BTC-USDC', 10)

# Sell specific amount
from trader import sell_crypto
sell_crypto('BTC-USDC', 0.0001)

# Check balances
from trader import get_all_balances
print(get_all_balances())
```

### Run the Smart Trader Bot

```bash
cd strategies
python smart_trader_v4.py
```

Configuration options:
- **Target Value** — Portfolio goal (default: $100)
- **Check Interval** — Minutes between analyses (default: 15)
- **Trade Percentage** — % of balance per trade (default: 50%)

### Run Sentiment Analysis Only

```bash
cd src
python sentiment_analyzer.py
```

Output:
```
📊 SENTIMENT ANALYSIS
============================================================
😱 Fear & Greed Index: 25 (Extreme Fear)
🔥 Reddit r/bitcoin: Score +42.5
💬 Reddit r/cryptocurrency: Score +18.2
📰 News Headlines: Score -12.0

🚀 OVERALL: BULLISH
   Combined Signal: +1.45 (scale: -3 to +3)
```

---

## 📈 Strategies

### 1. DCA Strategy (Safest)
```bash
python strategies/dca_strategy.py
```
- Buys fixed amount at regular intervals
- Ignores price movements
- Best for long-term accumulation

### 2. Grid Strategy (Medium Risk)
```bash
python strategies/grid_strategy.py
```
- Places buy orders below current price
- Places sell orders above current price
- Profits from sideways volatility

### 3. Momentum Strategy (Higher Risk)
```bash
python strategies/momentum_strategy.py
```
- Pure technical analysis
- RSI + MACD + Moving Averages
- Includes backtesting capability

### 4. Smart Trader v4 (Adaptive AI)
```bash
python strategies/smart_trader_v4.py
```
- Combines technical + sentiment analysis
- Learns from past trades
- Adapts thresholds based on performance
- Built-in risk management

---

## 🔬 Technical Details

### Signal Calculation

The bot generates trading signals by combining multiple indicators:

```
Technical Signal (70% weight)
├── RSI < 35        → +1 (oversold)
├── RSI > 65        → -1 (overbought)
├── MACD crossover  → ±1
├── Price vs SMA-25 → ±1
└── Bollinger Bands → ±1

Sentiment Signal (30% weight)
├── Fear & Greed Index (1.5x weight)
├── Reddit r/bitcoin sentiment
├── Reddit r/cryptocurrency sentiment
└── News headline sentiment

Final Signal = (Tech × 0.7) + (Sentiment × 0.3)

Action:
  Signal ≥ +1.0  → BUY
  Signal ≤ -1.0  → SELL
  Otherwise      → HOLD
```

### Risk Management

The trading brain implements automatic safeguards:

| Rule | Trigger | Action |
|------|---------|--------|
| Consecutive Losses | 3 losses in a row | Pause trading |
| Drawdown Limit | Portfolio down 10% | Stop bot |
| Position Awareness | Already holding | Skip buy signals |
| Adaptive Thresholds | Low win rate | Require stronger signals |

### Memory System

All trades are persisted in `trading_memory.json`:

```json
{
  "trades": [
    {
      "id": 1,
      "timestamp": "2024-12-03T10:30:00",
      "action": "BUY",
      "amount": 15.00,
      "price": 95420.50,
      "reasoning": "RSI oversold at 28. Fear & Greed at 22 (Extreme Fear)...",
      "outcome": "WIN",
      "profit_loss_pct": 2.35
    }
  ],
  "settings": {
    "max_consecutive_losses": 3,
    "max_daily_loss_percent": 10
  }
}
```

---

## 📊 Backtesting Results

180-day backtest on BTC-USDC:

| Metric | Momentum Strategy | Buy & Hold |
|--------|-------------------|------------|
| Return | -4.5% | -19.6% |
| Max Drawdown | -12% | -35% |
| Trades | 2 | 1 |

> The strategy **outperformed buy-and-hold by 15%** during a bearish period by avoiding major drawdowns.

---

## ⚠️ Disclaimer

**This software is for educational purposes only.**

- Cryptocurrency trading involves substantial risk of loss
- Past performance does not guarantee future results
- Never invest more than you can afford to lose
- The authors are not responsible for any financial losses

---

## 🛣 Roadmap

- [x] Technical analysis engine
- [x] Sentiment analysis module
- [x] Adaptive learning brain
- [x] Risk management system
- [ ] Machine learning price prediction
- [ ] Discord/Telegram notifications
- [ ] Web dashboard interface
- [ ] Multi-asset portfolio management

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Yaseen**
- Computer Science Student @ California State University Dominguez Hills
---

<p align="center">
  <strong>⭐ Star this repo if you found it useful! ⭐</strong>
</p>
