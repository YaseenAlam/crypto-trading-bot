"""
Smart Accumulator Bot v2
Uses HOURLY data from Coinbase for real intraday trading signals

Goal: Grow portfolio to $100 worth of BTC through signal-based trading

⚠️  WARNING: This trades REAL money. You can lose money.
Press Ctrl+C to stop the bot at any time.
"""

import os
import sys
import time
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from trader import buy_crypto, sell_crypto, get_account_balance, get_all_balances
from coinbase_client import get_coinbase_client, get_current_price


def get_hourly_data(product_id: str = "BTC-USDC", hours: int = 100) -> pd.DataFrame:
    """
    Fetch HOURLY candles directly from Coinbase.
    This updates every hour, not daily like CoinGecko.
    """
    from datetime import datetime, timedelta
    
    client = get_coinbase_client()
    
    end = datetime.now()
    start = end - timedelta(hours=hours)
    
    start_ts = int(start.timestamp())
    end_ts = int(end.timestamp())
    
    candles = client.get_candles(
        product_id=product_id,
        start=str(start_ts),
        end=str(end_ts),
        granularity="ONE_HOUR"
    )
    
    # Handle response format
    candle_list = candles.candles if hasattr(candles, 'candles') else candles.get('candles', [])
    
    data = []
    for candle in candle_list:
        if hasattr(candle, 'start'):
            data.append({
                'timestamp': datetime.fromtimestamp(int(candle.start)),
                'open': float(candle.open),
                'high': float(candle.high),
                'low': float(candle.low),
                'close': float(candle.close),
                'volume': float(candle.volume)
            })
        else:
            data.append({
                'timestamp': datetime.fromtimestamp(int(candle['start'])),
                'open': float(candle['open']),
                'high': float(candle['high']),
                'low': float(candle['low']),
                'close': float(candle['close']),
                'volume': float(candle['volume'])
            })
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values('timestamp').reset_index(drop=True)
        df.set_index('timestamp', inplace=True)
    
    return df


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators optimized for hourly data."""
    df = df.copy()
    
    # Shorter SMAs for hourly (7 hours, 25 hours instead of days)
    df['SMA_7'] = df['close'].rolling(window=7).mean()
    df['SMA_25'] = df['close'].rolling(window=25).mean()
    
    # EMAs for MACD
    df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
    
    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # RSI (14 period)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    df['BB_Middle'] = df['close'].rolling(window=20).mean()
    std = df['close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (std * 2)
    
    return df


class SmartAccumulatorBot:
    """
    Trades based on HOURLY technical signals to grow portfolio to target value.
    """
    
    def __init__(
        self,
        product_id: str = "BTC-USDC",
        target_value: float = 100.0,
        trade_percent: float = 50.0,
        check_interval_minutes: int = 15,
        rsi_oversold: float = 35.0,
        rsi_overbought: float = 65.0
    ):
        self.product_id = product_id
        self.target_value = target_value
        self.trade_percent = trade_percent / 100
        self.check_interval = check_interval_minutes * 60
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.base_currency = product_id.split('-')[0]
        
        self.trades_made = []
        self.start_time = datetime.now()
        self.last_analysis = None
        
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
        """Analyze market using HOURLY data."""
        try:
            # Get hourly candles from Coinbase
            df = get_hourly_data(self.product_id, hours=100)
            
            if len(df) < 30:
                return {'action': 'HOLD', 'reason': f'Not enough data ({len(df)} candles)', 'signal_strength': 0}
            
            df = add_indicators(df)
            df = df.dropna()
            
            if len(df) < 2:
                return {'action': 'HOLD', 'reason': 'Not enough data after indicators', 'signal_strength': 0}
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            rsi = latest['RSI']
            macd = latest['MACD']
            macd_signal = latest['MACD_Signal']
            price = latest['close']
            sma_7 = latest['SMA_7']
            sma_25 = latest['SMA_25']
            bb_lower = latest['BB_Lower']
            bb_upper = latest['BB_Upper']
            
            signals = []
            signal_strength = 0
            
            # RSI signals
            if rsi < self.rsi_oversold:
                signals.append(f"🟢 RSI oversold ({rsi:.1f} < {self.rsi_oversold})")
                signal_strength += 1
            elif rsi > self.rsi_overbought:
                signals.append(f"🔴 RSI overbought ({rsi:.1f} > {self.rsi_overbought})")
                signal_strength -= 1
            else:
                signals.append(f"⚪ RSI neutral ({rsi:.1f})")
            
            # MACD crossover signals
            macd_crossed_up = prev['MACD'] < prev['MACD_Signal'] and macd > macd_signal
            macd_crossed_down = prev['MACD'] > prev['MACD_Signal'] and macd < macd_signal
            
            if macd_crossed_up:
                signals.append("🟢 MACD bullish crossover!")
                signal_strength += 1
            elif macd_crossed_down:
                signals.append("🔴 MACD bearish crossover!")
                signal_strength -= 1
            elif macd > macd_signal:
                signals.append("⚪ MACD bullish (no crossover)")
            else:
                signals.append("⚪ MACD bearish (no crossover)")
            
            # Price vs SMA
            if price > sma_25:
                signals.append("🟢 Price above SMA-25 (uptrend)")
                signal_strength += 1
            else:
                signals.append("🔴 Price below SMA-25 (downtrend)")
                signal_strength -= 1
            
            # Bollinger Band signals (bonus)
            if price < bb_lower:
                signals.append("🟢 Price below lower Bollinger Band (oversold)")
                signal_strength += 1
            elif price > bb_upper:
                signals.append("🔴 Price above upper Bollinger Band (overbought)")
                signal_strength -= 1
            
            # Determine action (need 2+ for action)
            if signal_strength >= 2:
                action = "BUY"
            elif signal_strength <= -2:
                action = "SELL"
            else:
                action = "HOLD"
            
            analysis = {
                'action': action,
                'signal_strength': signal_strength,
                'signals': signals,
                'rsi': round(rsi, 1),
                'macd': round(macd, 2),
                'macd_signal': round(macd_signal, 2),
                'price': round(price, 2),
                'sma_7': round(sma_7, 2),
                'sma_25': round(sma_25, 2),
                'data_points': len(df),
                'latest_candle': df.index[-1].strftime('%Y-%m-%d %H:%M')
            }
            
            self.last_analysis = analysis
            return analysis
            
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
                
                buy_amount = max(1, usdc * self.trade_percent)
                buy_amount = min(buy_amount, usdc - 0.5)
                
                if buy_amount < 1:
                    print("   ⚠️  Buy amount too small")
                    return False
                
                print(f"\n   🟢 BUYING ${buy_amount:.2f} of BTC...")
                buy_crypto(self.product_id, buy_amount)
                self.trades_made.append({
                    'time': datetime.now(), 
                    'action': 'BUY', 
                    'amount': buy_amount,
                    'price': portfolio['price']
                })
                return True
                
            elif action == "SELL":
                crypto = portfolio['crypto']
                if crypto <= 0:
                    print("   ⚠️  No BTC to sell")
                    return False
                
                sell_amount = crypto * self.trade_percent
                
                if sell_amount * portfolio['price'] < 1:
                    print("   ⚠️  Sell amount too small")
                    return False
                
                print(f"\n   🔴 SELLING {sell_amount:.8f} BTC...")
                sell_crypto(self.product_id, sell_amount)
                self.trades_made.append({
                    'time': datetime.now(), 
                    'action': 'SELL', 
                    'amount': sell_amount,
                    'price': portfolio['price']
                })
                return True
                
        except Exception as e:
            print(f"   ❌ Trade failed: {e}")
            return False
        
        return False
    
    def display_status(self, portfolio: dict, analysis: dict):
        """Display current status."""
        print("\n" + "=" * 65)
        print(f"🤖 SMART ACCUMULATOR v2 (HOURLY) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 65)
        
        # Progress bar
        print(f"🎯 Target: ${self.target_value:.2f} | Current: ${portfolio['total_value']:.2f}")
        progress = min(100, (portfolio['total_value'] / self.target_value) * 100)
        bar = "█" * int(progress // 5) + "░" * (20 - int(progress // 5))
        print(f"   [{bar}] {progress:.1f}%")
        
        # Portfolio
        print(f"\n💰 Portfolio:")
        print(f"   USDC: ${portfolio['usdc']:.2f}")
        print(f"   BTC:  {portfolio['crypto']:.8f} (${portfolio['crypto_value']:.2f})")
        print(f"   BTC Price: ${portfolio['price']:,.2f}")
        
        # Analysis
        print(f"\n📊 Hourly Analysis (using {analysis.get('data_points', '?')} candles):")
        print(f"   Latest candle: {analysis.get('latest_candle', 'N/A')}")
        print(f"   RSI: {analysis.get('rsi', 'N/A')}")
        print(f"   MACD: {analysis.get('macd', 'N/A')} | Signal: {analysis.get('macd_signal', 'N/A')}")
        
        print(f"\n🎯 Signals:")
        if 'signals' in analysis:
            for sig in analysis['signals']:
                print(f"   {sig}")
        elif 'reason' in analysis:
            print(f"   {analysis['reason']}")
        
        print(f"\n📍 Signal Strength: {analysis.get('signal_strength', 0)}")
        print(f"🤖 Action: {analysis['action']}")
        
        # Trade history
        print(f"\n📈 Session Stats:")
        print(f"   Trades made: {len(self.trades_made)}")
        print(f"   Running since: {self.start_time.strftime('%H:%M:%S')}")
        
        print("=" * 65)
    
    def run(self):
        """Main bot loop."""
        print("\n" + "=" * 65)
        print("🚀 STARTING SMART ACCUMULATOR BOT v2 (HOURLY DATA)")
        print("=" * 65)
        print(f"Target: ${self.target_value:.2f} of portfolio value")
        print(f"Check interval: {self.check_interval // 60} minutes")
        print(f"Trade size: {self.trade_percent * 100:.0f}% of available balance")
        print(f"RSI Buy threshold: < {self.rsi_oversold}")
        print(f"RSI Sell threshold: > {self.rsi_overbought}")
        print(f"\n📡 Using HOURLY candles from Coinbase (updates every hour)")
        print("\nPress Ctrl+C to stop the bot")
        print("=" * 65)
        
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
                    runtime = datetime.now() - self.start_time
                    print(f"   Runtime: {runtime}")
                    print("🎉" * 20)
                    break
                
                # Analyze market with hourly data
                analysis = self.analyze()
                
                # Display status
                self.display_status(portfolio, analysis)
                
                # Execute trade if signal is strong enough
                action = analysis['action']
                if action == "BUY":
                    self.execute_trade(action, portfolio)
                elif action == "SELL":
                    self.execute_trade(action, portfolio)
                else:
                    print(f"\n   ⏸️  HOLDING - Signal strength ({analysis.get('signal_strength', 0)}) not strong enough")
                
                # Wait for next check
                print(f"\n⏰ Next check in {self.check_interval // 60} minutes...")
                print("   (Press Ctrl+C to stop)")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n\n" + "=" * 65)
            print("🛑 BOT STOPPED BY USER")
            print("=" * 65)
            portfolio = self.get_portfolio_value()
            print(f"Final portfolio value: ${portfolio['total_value']:.2f}")
            print(f"USDC: ${portfolio['usdc']:.2f}")
            print(f"BTC: {portfolio['crypto']:.8f} (${portfolio['crypto_value']:.2f})")
            print(f"Total trades made: {len(self.trades_made)}")
            if self.trades_made:
                print(f"\nTrade history:")
                for t in self.trades_made:
                    print(f"   {t['time'].strftime('%H:%M')} - {t['action']} @ ${t['price']:,.2f}")
            print("=" * 65)


def main():
    print("=" * 65)
    print("🤖 SMART ACCUMULATOR BOT v2 - SETUP")
    print("   Now using HOURLY data from Coinbase!")
    print("=" * 65)
    
    # Show current balance
    print("\n💰 Current Balances:")
    balances = get_all_balances()
    for currency, balance in balances.items():
        print(f"   {currency}: {balance}")
    
    # Get current price
    try:
        price = get_current_price("BTC-USDC")
        print(f"\n📈 Current BTC Price: ${price:,.2f}")
    except:
        pass
    
    print("\n" + "-" * 65)
    print("Configuration (press Enter for defaults):")
    print("-" * 65)
    
    target = input("Target portfolio value in $ (default 100): ").strip() or "100"
    interval = input("Check interval in minutes (default 15): ").strip() or "15"
    trade_pct = input("Trade % of balance per signal (default 50): ").strip() or "50"
    
    print("\n⚠️  WARNING: This bot trades REAL money!")
    print("   You could lose your investment.")
    print("   The bot uses HOURLY data so signals change throughout the day.")
    confirm = input("\nStart the bot? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("Cancelled.")
        return
    
    bot = SmartAccumulatorBot(
        product_id="BTC-USDC",
        target_value=float(target),
        check_interval_minutes=int(interval),
        trade_percent=float(trade_pct)
    )
    
    bot.run()


if __name__ == "__main__":
    main()
