"""
Smart Accumulator Bot
Goal: Grow portfolio to $100 worth of BTC through signal-based trading

⚠️  WARNING: This trades REAL money. You can lose money.
Press Ctrl+C to stop the bot at any time.
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from trader import buy_crypto, sell_crypto, get_account_balance, get_all_balances
from coinbase_client import get_current_price
from data_fetcher import get_crypto_data_free, add_technical_indicators


class SmartAccumulatorBot:
    """
    Trades based on technical signals to grow portfolio to target value.
    """
    
    def __init__(
        self,
        product_id: str = "BTC-USDC",
        coin_id: str = "bitcoin",
        target_value: float = 100.0,
        trade_percent: float = 50.0,  # Trade 50% of available balance
        check_interval_minutes: int = 30,
        rsi_oversold: float = 35.0,
        rsi_overbought: float = 65.0
    ):
        self.product_id = product_id
        self.coin_id = coin_id
        self.target_value = target_value
        self.trade_percent = trade_percent / 100
        self.check_interval = check_interval_minutes * 60  # Convert to seconds
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.base_currency = product_id.split('-')[0]  # BTC
        
        self.trades_made = []
        self.start_time = datetime.now()
        
    def get_portfolio_value(self) -> dict:
        """Calculate total portfolio value in USD."""
        usdc = get_account_balance("USDC")
        crypto = get_account_balance(self.base_currency)
        
        try:
            price = get_current_price(self.product_id)
        except:
            price = 0
        
        crypto_value = crypto * price
        total_value = usdc + crypto_value
        
        return {
            'usdc': round(usdc, 2),
            'crypto': crypto,
            'crypto_value': round(crypto_value, 2),
            'total_value': round(total_value, 2),
            'price': round(price, 2)
        }
    
    def analyze(self) -> dict:
        """Analyze market and return signal."""
        try:
            df = get_crypto_data_free(self.coin_id, days=120)
            df = add_technical_indicators(df)
            df = df.dropna()
            
            if len(df) < 2:
                return {'action': 'HOLD', 'reason': 'Not enough data', 'signal_strength': 0}
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            rsi = latest['RSI']
            macd = latest['MACD']
            macd_signal = latest['MACD_Signal']
            price = latest['close']
            sma_25 = latest['SMA_25']
            
            signals = []
            signal_strength = 0
            
            # RSI
            if rsi < self.rsi_oversold:
                signals.append(f"RSI oversold ({rsi:.1f})")
                signal_strength += 1
            elif rsi > self.rsi_overbought:
                signals.append(f"RSI overbought ({rsi:.1f})")
                signal_strength -= 1
            
            # MACD crossover
            if prev['MACD'] < prev['MACD_Signal'] and macd > macd_signal:
                signals.append("MACD bullish crossover")
                signal_strength += 1
            elif prev['MACD'] > prev['MACD_Signal'] and macd < macd_signal:
                signals.append("MACD bearish crossover")
                signal_strength -= 1
            
            # Price vs SMA
            if price > sma_25:
                signals.append("Price above SMA-25")
                signal_strength += 1
            else:
                signals.append("Price below SMA-25")
                signal_strength -= 1
            
            # Determine action
            if signal_strength >= 2:
                action = "BUY"
            elif signal_strength <= -2:
                action = "SELL"
            else:
                action = "HOLD"
            
            return {
                'action': action,
                'signal_strength': signal_strength,
                'signals': signals,
                'rsi': round(rsi, 1),
                'price': round(price, 2)
            }
            
        except Exception as e:
            return {'action': 'HOLD', 'reason': f'Analysis error: {e}', 'signal_strength': 0}
    
    def execute_trade(self, action: str, portfolio: dict) -> bool:
        """Execute a trade based on signal."""
        try:
            if action == "BUY":
                usdc = portfolio['usdc']
                if usdc < 1:
                    print("   ⚠️  Not enough USDC to buy")
                    return False
                
                # Buy with a portion of available USDC
                buy_amount = max(1, usdc * self.trade_percent)
                buy_amount = min(buy_amount, usdc - 0.5)  # Leave a small buffer
                
                if buy_amount < 1:
                    print("   ⚠️  Buy amount too small")
                    return False
                
                print(f"   🟢 BUYING ${buy_amount:.2f} of BTC...")
                buy_crypto(self.product_id, buy_amount)
                self.trades_made.append({'time': datetime.now(), 'action': 'BUY', 'amount': buy_amount})
                return True
                
            elif action == "SELL":
                crypto = portfolio['crypto']
                if crypto <= 0:
                    print("   ⚠️  No BTC to sell")
                    return False
                
                # Sell a portion of crypto
                sell_amount = crypto * self.trade_percent
                
                if sell_amount * portfolio['price'] < 1:
                    print("   ⚠️  Sell amount too small")
                    return False
                
                print(f"   🔴 SELLING {sell_amount:.8f} BTC...")
                sell_crypto(self.product_id, sell_amount)
                self.trades_made.append({'time': datetime.now(), 'action': 'SELL', 'amount': sell_amount})
                return True
                
        except Exception as e:
            print(f"   ❌ Trade failed: {e}")
            return False
        
        return False
    
    def display_status(self, portfolio: dict, analysis: dict):
        """Display current status."""
        print("\n" + "=" * 60)
        print(f"🤖 SMART ACCUMULATOR BOT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print(f"🎯 Target: ${self.target_value:.2f} | Current: ${portfolio['total_value']:.2f}")
        progress = min(100, (portfolio['total_value'] / self.target_value) * 100)
        bar = "█" * int(progress // 5) + "░" * (20 - int(progress // 5))
        print(f"   [{bar}] {progress:.1f}%")
        print(f"\n💰 Portfolio:")
        print(f"   USDC: ${portfolio['usdc']:.2f}")
        print(f"   BTC:  {portfolio['crypto']:.8f} (${portfolio['crypto_value']:.2f})")
        print(f"   BTC Price: ${portfolio['price']:,.2f}")
        print(f"\n📊 Analysis:")
        print(f"   RSI: {analysis.get('rsi', 'N/A')}")
        print(f"   Signal: {analysis['action']} (strength: {analysis['signal_strength']})")
        if 'signals' in analysis:
            for sig in analysis['signals']:
                print(f"   • {sig}")
        print(f"\n📈 Trades made this session: {len(self.trades_made)}")
        print("=" * 60)
    
    def run(self):
        """Main bot loop."""
        print("\n" + "=" * 60)
        print("🚀 STARTING SMART ACCUMULATOR BOT")
        print("=" * 60)
        print(f"Target: ${self.target_value:.2f} of BTC")
        print(f"Check interval: {self.check_interval // 60} minutes")
        print(f"Trade size: {self.trade_percent * 100:.0f}% of available balance")
        print(f"RSI thresholds: Buy < {self.rsi_oversold}, Sell > {self.rsi_overbought}")
        print("\nPress Ctrl+C to stop the bot")
        print("=" * 60)
        
        try:
            while True:
                # Get portfolio value
                portfolio = self.get_portfolio_value()
                
                # Check if target reached
                if portfolio['total_value'] >= self.target_value:
                    print("\n" + "🎉" * 20)
                    print(f"🎯 TARGET REACHED! Portfolio: ${portfolio['total_value']:.2f}")
                    print(f"   BTC held: {portfolio['crypto']:.8f}")
                    print(f"   Total trades: {len(self.trades_made)}")
                    print("🎉" * 20)
                    break
                
                # Analyze market
                analysis = self.analyze()
                
                # Display status
                self.display_status(portfolio, analysis)
                
                # Execute trade if signal is strong enough
                action = analysis['action']
                if action in ["BUY", "SELL"]:
                    self.execute_trade(action, portfolio)
                else:
                    print(f"\n   ⏸️  HOLDING - waiting for stronger signal")
                
                # Wait for next check
                print(f"\n⏰ Next check in {self.check_interval // 60} minutes...")
                print("   (Press Ctrl+C to stop)")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n\n" + "=" * 60)
            print("🛑 BOT STOPPED BY USER")
            print("=" * 60)
            portfolio = self.get_portfolio_value()
            print(f"Final portfolio value: ${portfolio['total_value']:.2f}")
            print(f"USDC: ${portfolio['usdc']:.2f}")
            print(f"BTC: {portfolio['crypto']:.8f} (${portfolio['crypto_value']:.2f})")
            print(f"Total trades made: {len(self.trades_made)}")
            print("=" * 60)


def main():
    print("=" * 60)
    print("🤖 SMART ACCUMULATOR BOT SETUP")
    print("=" * 60)
    
    # Show current balance
    print("\n💰 Current Balances:")
    balances = get_all_balances()
    for currency, balance in balances.items():
        print(f"   {currency}: {balance}")
    
    print("\n" + "-" * 60)
    print("Configuration:")
    print("-" * 60)
    
    target = input("Target portfolio value in $ (default 100): ").strip() or "100"
    interval = input("Check interval in minutes (default 30): ").strip() or "30"
    trade_pct = input("Trade % of balance per signal (default 50): ").strip() or "50"
    
    print("\n⚠️  WARNING: This bot trades REAL money!")
    print("   You could lose your investment.")
    confirm = input("\nStart the bot? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("Cancelled.")
        return
    
    bot = SmartAccumulatorBot(
        product_id="BTC-USDC",
        coin_id="bitcoin",
        target_value=float(target),
        check_interval_minutes=int(interval),
        trade_percent=float(trade_pct)
    )
    
    bot.run()


if __name__ == "__main__":
    main()
