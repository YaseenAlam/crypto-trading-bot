"""
Smart Accumulator Bot v4 - WITH MEMORY & LEARNING

This bot:
- Remembers all trades and their outcomes
- Tracks win rate and adjusts strategy
- Has risk management (stops if losing too much)
- Generates reasoning for each decision
- Learns from mistakes

⚠️  WARNING: This trades REAL money.
Press Ctrl+C to stop at any time.
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from trader import buy_crypto, sell_crypto, get_account_balance, get_all_balances
from coinbase_client import get_coinbase_client, get_current_price
from sentiment_analyzer import get_combined_sentiment
from trading_brain import TradingBrain


def get_hourly_data(product_id: str = "BTC-USDC", hours: int = 100) -> pd.DataFrame:
    """Fetch HOURLY candles from Coinbase."""
    from datetime import datetime, timedelta
    
    client = get_coinbase_client()
    end = datetime.now()
    start = end - timedelta(hours=hours)
    
    candles = client.get_candles(
        product_id=product_id,
        start=str(int(start.timestamp())),
        end=str(int(end.timestamp())),
        granularity="ONE_HOUR"
    )
    
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
    """Add technical indicators."""
    df = df.copy()
    
    df['SMA_7'] = df['close'].rolling(window=7).mean()
    df['SMA_25'] = df['close'].rolling(window=25).mean()
    df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['BB_Middle'] = df['close'].rolling(window=20).mean()
    std = df['close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (std * 2)
    
    return df


class SmartTraderV4:
    """
    Intelligent trading bot with memory and learning.
    """
    
    def __init__(
        self,
        product_id: str = "BTC-USDC",
        target_value: float = 100.0,
        trade_percent: float = 50.0,
        check_interval_minutes: int = 15,
        sentiment_weight: float = 0.3
    ):
        self.product_id = product_id
        self.target_value = target_value
        self.trade_percent = trade_percent / 100
        self.check_interval = check_interval_minutes * 60
        self.sentiment_weight = sentiment_weight
        self.base_currency = product_id.split('-')[0]
        
        # Initialize the brain
        self.brain = TradingBrain("trading_memory.json")
        
        self.start_time = datetime.now()
        self.session_trades = 0
    
    def get_portfolio(self) -> dict:
        """Get current portfolio value."""
        usdc = get_account_balance("USDC")
        crypto = get_account_balance(self.base_currency)
        
        try:
            price = get_current_price(self.product_id)
        except:
            price = 0
        
        crypto_value = crypto * price
        total = usdc + crypto_value
        
        return {
            'usdc': round(usdc, 2),
            'crypto': crypto,
            'crypto_value': round(crypto_value, 2),
            'total': round(total, 2),
            'price': round(price, 2)
        }
    
    def analyze_technical(self) -> dict:
        """Technical analysis with adaptive thresholds."""
        thresholds = self.brain.get_adaptive_thresholds()
        
        try:
            df = get_hourly_data(self.product_id, hours=100)
            if len(df) < 30:
                return {'signal': 0, 'error': 'Not enough data'}
            
            df = add_indicators(df)
            df = df.dropna()
            
            if len(df) < 2:
                return {'signal': 0, 'error': 'Not enough data after indicators'}
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            rsi = latest['RSI']
            macd = latest['MACD']
            macd_signal = latest['MACD_Signal']
            price = latest['close']
            sma_25 = latest['SMA_25']
            bb_lower = latest['BB_Lower']
            bb_upper = latest['BB_Upper']
            
            signal = 0
            signals = []
            
            # RSI with adaptive thresholds
            if rsi < thresholds['rsi_oversold']:
                signals.append(f"🟢 RSI {rsi:.0f} < {thresholds['rsi_oversold']} (oversold)")
                signal += 1
            elif rsi > thresholds['rsi_overbought']:
                signals.append(f"🔴 RSI {rsi:.0f} > {thresholds['rsi_overbought']} (overbought)")
                signal -= 1
            else:
                signals.append(f"⚪ RSI {rsi:.0f} (neutral)")
            
            # MACD crossover
            if prev['MACD'] < prev['MACD_Signal'] and macd > macd_signal:
                signals.append("🟢 MACD bullish crossover")
                signal += 1
            elif prev['MACD'] > prev['MACD_Signal'] and macd < macd_signal:
                signals.append("🔴 MACD bearish crossover")
                signal -= 1
            
            # Price vs SMA
            if price > sma_25:
                signals.append("🟢 Price > SMA-25")
                signal += 1
            else:
                signals.append("🔴 Price < SMA-25")
                signal -= 1
            
            # Bollinger
            if price < bb_lower:
                signals.append("🟢 Below lower BB")
                signal += 1
            elif price > bb_upper:
                signals.append("🔴 Above upper BB")
                signal -= 1
            
            return {
                'signal': signal,
                'signals': signals,
                'rsi': round(rsi, 1),
                'macd': round(macd, 2),
                'price': round(price, 2),
                'sma_25': round(sma_25, 2),
                'candle_time': df.index[-1].strftime('%H:%M')
            }
            
        except Exception as e:
            return {'signal': 0, 'error': str(e)}
    
    def analyze_sentiment(self) -> dict:
        """Get sentiment analysis."""
        try:
            return get_combined_sentiment()
        except Exception as e:
            return {'combined_signal': 0, 'overall': 'NEUTRAL', 'emoji': '😐'}
    
    def make_decision(self, tech: dict, sent: dict, portfolio: dict) -> dict:
        """Make a decision using technical, sentiment, and brain."""
        
        thresholds = self.brain.get_adaptive_thresholds()
        
        # Get signals
        tech_signal = tech.get('signal', 0)
        sent_signal = sent.get('combined_signal', 0)
        
        # Normalize tech to -3 to +3
        tech_norm = (tech_signal / 4) * 3
        
        # Combine
        tech_weight = 1 - self.sentiment_weight
        final_signal = (tech_norm * tech_weight) + (sent_signal * self.sentiment_weight)
        
        # Check open position
        open_pos = self.brain.get_open_position()
        
        # Determine action
        min_signal = thresholds['min_signal_strength']
        
        if final_signal >= min_signal:
            if open_pos:
                action = "HOLD"  # Already have position
                reason = "Signal says BUY but already holding. Will hold."
            else:
                action = "BUY"
                reason = "Strong buy signal, no current position."
        elif final_signal <= -min_signal:
            if open_pos:
                action = "SELL"
                reason = "Strong sell signal, closing position."
            else:
                action = "HOLD"  # Nothing to sell
                reason = "Signal says SELL but no position. Waiting."
        else:
            action = "HOLD"
            reason = f"Signal ({final_signal:.2f}) not strong enough (need >{min_signal:.1f} or <-{min_signal:.1f})."
        
        # Generate full reasoning
        full_reasoning = self.brain.generate_reasoning(action, tech, sent, portfolio)
        
        confidence = min(abs(final_signal) / 3 * 100, 100)
        
        return {
            'action': action,
            'final_signal': round(final_signal, 2),
            'tech_signal': round(tech_norm, 2),
            'sent_signal': round(sent_signal, 2),
            'confidence': round(confidence, 1),
            'reason': reason,
            'full_reasoning': full_reasoning,
            'min_signal_required': min_signal
        }
    
    def execute_trade(self, action: str, portfolio: dict, decision: dict, 
                      tech: dict, sent: dict) -> bool:
        """Execute trade and record to brain."""
        
        try:
            if action == "BUY":
                usdc = portfolio['usdc']
                if usdc < 1:
                    print("   ⚠️ Not enough USDC")
                    return False
                
                buy_amount = max(1, usdc * self.trade_percent)
                buy_amount = min(buy_amount, usdc - 0.5)
                
                if buy_amount < 1:
                    return False
                
                print(f"\n   🟢 BUYING ${buy_amount:.2f} of BTC...")
                buy_crypto(self.product_id, buy_amount)
                
                # Record to brain
                self.brain.record_trade(
                    action="BUY",
                    amount=buy_amount,
                    price=portfolio['price'],
                    reasoning=decision['full_reasoning'],
                    signals={
                        'tech': decision['tech_signal'],
                        'sent': decision['sent_signal'],
                        'final': decision['final_signal'],
                        'rsi': tech.get('rsi'),
                        'sentiment': sent.get('overall')
                    }
                )
                
                self.session_trades += 1
                return True
                
            elif action == "SELL":
                crypto = portfolio['crypto']
                if crypto <= 0:
                    print("   ⚠️ No BTC to sell")
                    return False
                
                sell_amount = crypto * self.trade_percent
                
                if sell_amount * portfolio['price'] < 1:
                    return False
                
                print(f"\n   🔴 SELLING {sell_amount:.8f} BTC...")
                sell_crypto(self.product_id, sell_amount)
                
                # Close position in brain
                self.brain.close_position(portfolio['price'], sell_amount)
                
                # Record the sell
                self.brain.record_trade(
                    action="SELL",
                    amount=sell_amount,
                    price=portfolio['price'],
                    reasoning=decision['full_reasoning'],
                    signals={
                        'tech': decision['tech_signal'],
                        'sent': decision['sent_signal'],
                        'final': decision['final_signal']
                    }
                )
                
                self.session_trades += 1
                return True
                
        except Exception as e:
            print(f"   ❌ Trade failed: {e}")
            return False
        
        return False
    
    def display_status(self, portfolio: dict, tech: dict, sent: dict, decision: dict):
        """Display comprehensive status."""
        
        stats = self.brain.get_performance_stats()
        open_pos = self.brain.get_open_position()
        thresholds = self.brain.get_adaptive_thresholds()
        
        print("\n" + "=" * 70)
        print(f"🤖 SMART TRADER v4 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("   Memory-enabled | Learning | Risk-managed")
        print("=" * 70)
        
        # Progress
        progress = min(100, (portfolio['total'] / self.target_value) * 100)
        bar = "█" * int(progress // 5) + "░" * (20 - int(progress // 5))
        print(f"\n🎯 Goal: ${self.target_value:.0f} | Current: ${portfolio['total']:.2f}")
        print(f"   [{bar}] {progress:.1f}%")
        
        # Portfolio
        print(f"\n💰 Portfolio:")
        print(f"   USDC: ${portfolio['usdc']:.2f}")
        print(f"   BTC: {portfolio['crypto']:.8f} (${portfolio['crypto_value']:.2f})")
        print(f"   Price: ${portfolio['price']:,.2f}")
        
        # Open position
        if open_pos:
            buy_price = open_pos['price']
            pct = ((portfolio['price'] - buy_price) / buy_price) * 100
            emoji = "📈" if pct > 0 else "📉"
            print(f"\n{emoji} Open Position:")
            print(f"   Bought at: ${buy_price:,.2f}")
            print(f"   Current P/L: {pct:+.2f}%")
        
        # Brain stats
        print(f"\n🧠 Brain Stats:")
        print(f"   Total trades: {stats['total_trades']}")
        if stats['closed_trades'] > 0:
            print(f"   Win rate: {stats['win_rate']}%")
            print(f"   Best: +{stats['best_trade']}% | Worst: {stats['worst_trade']}%")
            if stats['consecutive_losses'] > 0:
                print(f"   ⚠️ Consecutive losses: {stats['consecutive_losses']}")
        
        # Adaptive thresholds
        print(f"\n🎚️ Adaptive Settings:")
        print(f"   RSI buy < {thresholds['rsi_oversold']} | RSI sell > {thresholds['rsi_overbought']}")
        print(f"   Min signal strength: {thresholds['min_signal_strength']}")
        
        # Technical
        print(f"\n📈 Technical (weight: {(1-self.sentiment_weight)*100:.0f}%):")
        print(f"   Signal: {decision['tech_signal']:+.2f}")
        if 'signals' in tech:
            for sig in tech['signals'][:3]:
                print(f"   {sig}")
        
        # Sentiment
        print(f"\n📊 Sentiment (weight: {self.sentiment_weight*100:.0f}%):")
        print(f"   Signal: {decision['sent_signal']:+.2f}")
        fg = sent.get('fear_greed', {})
        print(f"   {fg.get('emoji', '😐')} Fear & Greed: {fg.get('value', '?')} ({fg.get('classification', '?')})")
        print(f"   Overall: {sent.get('overall', 'NEUTRAL')}")
        
        # Decision
        print(f"\n" + "-" * 70)
        print(f"🎲 DECISION: {decision['action']}")
        print(f"   Combined signal: {decision['final_signal']:+.2f}")
        print(f"   Confidence: {decision['confidence']:.0f}%")
        print(f"\n💭 Reasoning:")
        
        # Word wrap the reasoning
        reasoning = decision['full_reasoning']
        words = reasoning.split()
        line = "   "
        for word in words:
            if len(line) + len(word) > 68:
                print(line)
                line = "   " + word
            else:
                line += " " + word if line != "   " else word
        if line.strip():
            print(line)
        
        print("=" * 70)
    
    def run(self):
        """Main loop."""
        
        portfolio = self.get_portfolio()
        self.brain.set_starting_value(portfolio['total'])
        
        print("\n" + "=" * 70)
        print("🚀 STARTING SMART TRADER v4")
        print("=" * 70)
        print(f"Target: ${self.target_value}")
        print(f"Starting value: ${portfolio['total']:.2f}")
        print(f"Check interval: {self.check_interval // 60} min")
        print(f"\nThis bot remembers and learns from every trade.")
        print("Press Ctrl+C to stop")
        print("=" * 70)
        
        try:
            while True:
                portfolio = self.get_portfolio()
                
                # Update brain with current price
                self.brain.calculate_trade_outcome(portfolio['price'])
                
                # Check target
                if portfolio['total'] >= self.target_value:
                    print("\n" + "🎉" * 20)
                    print(f"TARGET REACHED! ${portfolio['total']:.2f}")
                    self.brain.display_memory_status()
                    break
                
                # Check risk limits
                should_stop, reason = self.brain.should_stop_trading(portfolio['total'])
                if should_stop:
                    print(f"\n⛔ RISK LIMIT: {reason}")
                    print("Bot pausing for safety. Restart manually when ready.")
                    self.brain.display_memory_status()
                    break
                
                # Analyze
                print("\n⏳ Analyzing...")
                tech = self.analyze_technical()
                sent = self.analyze_sentiment()
                decision = self.make_decision(tech, sent, portfolio)
                
                # Record decision
                self.brain.record_decision(
                    action=decision['action'],
                    reasoning=decision['reason'],
                    tech_signal=decision['tech_signal'],
                    sent_signal=decision['sent_signal'],
                    final_signal=decision['final_signal'],
                    confidence=decision['confidence']
                )
                
                # Display
                self.display_status(portfolio, tech, sent, decision)
                
                # Execute
                if decision['action'] in ["BUY", "SELL"]:
                    self.execute_trade(decision['action'], portfolio, decision, tech, sent)
                else:
                    print(f"\n   ⏸️ HOLDING")
                
                # Wait
                print(f"\n⏰ Next check in {self.check_interval // 60} min... (Ctrl+C to stop)")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n\n" + "=" * 70)
            print("🛑 BOT STOPPED")
            print("=" * 70)
            
            portfolio = self.get_portfolio()
            print(f"Final value: ${portfolio['total']:.2f}")
            print(f"Session trades: {self.session_trades}")
            
            self.brain.display_memory_status()
            
            print("\n💾 Memory saved. Bot will remember this session.")
            print("=" * 70)


def main():
    print("=" * 70)
    print("🤖 SMART TRADER v4 - SETUP")
    print("   Memory | Learning | Risk Management")
    print("=" * 70)
    
    # Check for existing memory
    if os.path.exists("trading_memory.json"):
        print("\n📂 Found existing trading memory!")
        brain = TradingBrain("trading_memory.json")
        brain.display_memory_status()
    
    # Balances
    print("\n💰 Current Balances:")
    balances = get_all_balances()
    for currency, balance in balances.items():
        print(f"   {currency}: {balance}")
    
    # Config
    print("\n" + "-" * 70)
    target = input("Target $ (default 100): ").strip() or "100"
    interval = input("Check interval mins (default 15): ").strip() or "15"
    trade_pct = input("Trade % per signal (default 50): ").strip() or "50"
    
    print("\n⚠️ This bot trades REAL money and remembers everything.")
    confirm = input("Start? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("Cancelled.")
        return
    
    bot = SmartTraderV4(
        product_id="BTC-USDC",
        target_value=float(target),
        check_interval_minutes=int(interval),
        trade_percent=float(trade_pct)
    )
    
    bot.run()


if __name__ == "__main__":
    main()
