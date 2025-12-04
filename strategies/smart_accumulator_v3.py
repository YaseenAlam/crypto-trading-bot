"""
Smart Accumulator Bot v3 - WITH SENTIMENT ANALYSIS
Uses HOURLY technical data + Reddit/News/Fear&Greed sentiment

Goal: Grow portfolio to $100 worth of BTC through smarter trading

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
from sentiment_analyzer import get_combined_sentiment, display_sentiment


def get_hourly_data(product_id: str = "BTC-USDC", hours: int = 100) -> pd.DataFrame:
    """Fetch HOURLY candles directly from Coinbase."""
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
    """Add technical indicators for hourly data."""
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


class SmartAccumulatorBotV3:
    """
    Trading bot that combines:
    - Technical Analysis (RSI, MACD, SMA, Bollinger Bands)
    - Sentiment Analysis (Fear & Greed, Reddit, News)
    """
    
    def __init__(
        self,
        product_id: str = "BTC-USDC",
        target_value: float = 100.0,
        trade_percent: float = 50.0,
        check_interval_minutes: int = 15,
        rsi_oversold: float = 35.0,
        rsi_overbought: float = 65.0,
        use_sentiment: bool = True,
        sentiment_weight: float = 0.3  # How much sentiment affects decision (0-1)
    ):
        self.product_id = product_id
        self.target_value = target_value
        self.trade_percent = trade_percent / 100
        self.check_interval = check_interval_minutes * 60
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.use_sentiment = use_sentiment
        self.sentiment_weight = sentiment_weight
        self.base_currency = product_id.split('-')[0]
        
        self.trades_made = []
        self.start_time = datetime.now()
        self.last_sentiment = None
        
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
    
    def analyze_technical(self) -> dict:
        """Analyze using technical indicators."""
        try:
            df = get_hourly_data(self.product_id, hours=100)
            
            if len(df) < 30:
                return {'signal': 0, 'reason': f'Not enough data ({len(df)} candles)'}
            
            df = add_indicators(df)
            df = df.dropna()
            
            if len(df) < 2:
                return {'signal': 0, 'reason': 'Not enough data after indicators'}
            
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            rsi = latest['RSI']
            macd = latest['MACD']
            macd_signal = latest['MACD_Signal']
            price = latest['close']
            sma_25 = latest['SMA_25']
            bb_lower = latest['BB_Lower']
            bb_upper = latest['BB_Upper']
            
            signals = []
            signal_strength = 0
            
            # RSI
            if rsi < self.rsi_oversold:
                signals.append(f"🟢 RSI oversold ({rsi:.1f})")
                signal_strength += 1
            elif rsi > self.rsi_overbought:
                signals.append(f"🔴 RSI overbought ({rsi:.1f})")
                signal_strength -= 1
            else:
                signals.append(f"⚪ RSI neutral ({rsi:.1f})")
            
            # MACD crossover
            macd_crossed_up = prev['MACD'] < prev['MACD_Signal'] and macd > macd_signal
            macd_crossed_down = prev['MACD'] > prev['MACD_Signal'] and macd < macd_signal
            
            if macd_crossed_up:
                signals.append("🟢 MACD bullish crossover")
                signal_strength += 1
            elif macd_crossed_down:
                signals.append("🔴 MACD bearish crossover")
                signal_strength -= 1
            else:
                signals.append("⚪ MACD no crossover")
            
            # Price vs SMA
            if price > sma_25:
                signals.append("🟢 Above SMA-25")
                signal_strength += 1
            else:
                signals.append("🔴 Below SMA-25")
                signal_strength -= 1
            
            # Bollinger Bands
            if price < bb_lower:
                signals.append("🟢 Below lower BB")
                signal_strength += 1
            elif price > bb_upper:
                signals.append("🔴 Above upper BB")
                signal_strength -= 1
            
            return {
                'signal': signal_strength,
                'signals': signals,
                'rsi': round(rsi, 1),
                'macd': round(macd, 2),
                'price': round(price, 2),
                'sma_25': round(sma_25, 2),
                'latest_candle': df.index[-1].strftime('%Y-%m-%d %H:%M')
            }
            
        except Exception as e:
            return {'signal': 0, 'reason': f'Technical analysis error: {e}'}
    
    def analyze_sentiment(self) -> dict:
        """Get sentiment analysis."""
        try:
            sentiment = get_combined_sentiment()
            self.last_sentiment = sentiment
            return sentiment
        except Exception as e:
            return {'combined_signal': 0, 'overall': 'NEUTRAL', 'emoji': '😐'}
    
    def make_decision(self, technical: dict, sentiment: dict) -> dict:
        """
        Combine technical and sentiment analysis for final decision.
        
        Technical signal: -4 to +4 (from indicators)
        Sentiment signal: -3 to +3 (from sentiment)
        
        Final decision weighted combination.
        """
        tech_signal = technical.get('signal', 0)
        sent_signal = sentiment.get('combined_signal', 0)
        
        # Normalize technical to -3 to +3 scale (same as sentiment)
        tech_normalized = (tech_signal / 4) * 3
        
        # Weighted combination
        tech_weight = 1 - self.sentiment_weight
        final_signal = (tech_normalized * tech_weight) + (sent_signal * self.sentiment_weight)
        
        # Determine action
        # Need signal >= 1.0 to act (fairly conservative)
        if final_signal >= 1.0:
            action = "BUY"
            confidence = min(final_signal / 3 * 100, 100)
        elif final_signal <= -1.0:
            action = "SELL"
            confidence = min(abs(final_signal) / 3 * 100, 100)
        else:
            action = "HOLD"
            confidence = 0
        
        return {
            'action': action,
            'final_signal': round(final_signal, 2),
            'tech_signal': round(tech_normalized, 2),
            'sent_signal': round(sent_signal, 2),
            'confidence': round(confidence, 1),
            'tech_weight': f"{tech_weight*100:.0f}%",
            'sent_weight': f"{self.sentiment_weight*100:.0f}%"
        }
    
    def execute_trade(self, action: str, portfolio: dict) -> bool:
        """Execute a trade based on decision."""
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
                    'amount_usd': buy_amount,
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
                    'amount_btc': sell_amount,
                    'price': portfolio['price']
                })
                return True
                
        except Exception as e:
            print(f"   ❌ Trade failed: {e}")
            return False
        
        return False
    
    def display_status(self, portfolio: dict, technical: dict, sentiment: dict, decision: dict):
        """Display comprehensive status."""
        print("\n" + "=" * 70)
        print(f"🤖 SMART ACCUMULATOR v3 (TECHNICAL + SENTIMENT)")
        print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        # Progress
        progress = min(100, (portfolio['total_value'] / self.target_value) * 100)
        bar = "█" * int(progress // 5) + "░" * (20 - int(progress // 5))
        print(f"\n🎯 Target: ${self.target_value:.2f} | Current: ${portfolio['total_value']:.2f}")
        print(f"   [{bar}] {progress:.1f}%")
        
        # Portfolio
        print(f"\n💰 Portfolio:")
        print(f"   USDC: ${portfolio['usdc']:.2f}")
        print(f"   BTC:  {portfolio['crypto']:.8f} (${portfolio['crypto_value']:.2f})")
        print(f"   Price: ${portfolio['price']:,.2f}")
        
        # Technical Analysis
        print(f"\n📈 TECHNICAL ANALYSIS (Weight: {decision['tech_weight']})")
        print(f"   Signal: {decision['tech_signal']:+.2f}")
        if 'signals' in technical:
            for sig in technical['signals']:
                print(f"   {sig}")
        
        # Sentiment Analysis
        print(f"\n📊 SENTIMENT ANALYSIS (Weight: {decision['sent_weight']})")
        print(f"   Signal: {decision['sent_signal']:+.2f}")
        
        fg = sentiment.get('fear_greed', {})
        print(f"   {fg.get('emoji', '😐')} Fear & Greed: {fg.get('value', 'N/A')} ({fg.get('classification', 'N/A')})")
        
        rb = sentiment.get('reddit_bitcoin', {})
        print(f"   🔥 Reddit r/bitcoin: {rb.get('score', 0):+.1f}")
        
        rc = sentiment.get('reddit_crypto', {})
        print(f"   💬 Reddit r/crypto: {rc.get('score', 0):+.1f}")
        
        news = sentiment.get('news', {})
        print(f"   📰 News: {news.get('score', 0):+.1f}")
        
        print(f"\n   {sentiment.get('emoji', '😐')} Overall Sentiment: {sentiment.get('overall', 'NEUTRAL')}")
        
        # Final Decision
        print(f"\n" + "-" * 70)
        print(f"🎲 FINAL DECISION")
        print(f"   Combined Signal: {decision['final_signal']:+.2f} (scale: -3 to +3)")
        print(f"   Action: {decision['action']}")
        if decision['confidence'] > 0:
            print(f"   Confidence: {decision['confidence']:.0f}%")
        
        # Session stats
        print(f"\n📊 Session: {len(self.trades_made)} trades | Running: {datetime.now() - self.start_time}")
        print("=" * 70)
    
    def run(self):
        """Main bot loop."""
        print("\n" + "=" * 70)
        print("🚀 SMART ACCUMULATOR BOT v3")
        print("   Technical Analysis + Sentiment Analysis")
        print("=" * 70)
        print(f"\nConfiguration:")
        print(f"   Target: ${self.target_value:.2f}")
        print(f"   Check interval: {self.check_interval // 60} minutes")
        print(f"   Trade size: {self.trade_percent * 100:.0f}% of balance")
        print(f"   Technical weight: {(1-self.sentiment_weight)*100:.0f}%")
        print(f"   Sentiment weight: {self.sentiment_weight*100:.0f}%")
        print(f"\nPress Ctrl+C to stop")
        print("=" * 70)
        
        try:
            while True:
                portfolio = self.get_portfolio_value()
                
                # Check target
                if portfolio['total_value'] >= self.target_value:
                    print("\n" + "🎉" * 20)
                    print(f"🎯 TARGET REACHED! ${portfolio['total_value']:.2f}")
                    print(f"   BTC: {portfolio['crypto']:.8f}")
                    print(f"   Trades: {len(self.trades_made)}")
                    print("🎉" * 20)
                    break
                
                # Analyze
                print("\n⏳ Analyzing market...")
                technical = self.analyze_technical()
                
                print("   📡 Fetching sentiment...")
                sentiment = self.analyze_sentiment()
                
                # Make decision
                decision = self.make_decision(technical, sentiment)
                
                # Display
                self.display_status(portfolio, technical, sentiment, decision)
                
                # Execute
                action = decision['action']
                if action in ["BUY", "SELL"]:
                    self.execute_trade(action, portfolio)
                else:
                    print(f"\n   ⏸️  HOLDING - Signal ({decision['final_signal']:+.2f}) not strong enough")
                
                # Wait
                print(f"\n⏰ Next check in {self.check_interval // 60} minutes... (Ctrl+C to stop)")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n\n" + "=" * 70)
            print("🛑 BOT STOPPED")
            print("=" * 70)
            portfolio = self.get_portfolio_value()
            print(f"Final value: ${portfolio['total_value']:.2f}")
            print(f"USDC: ${portfolio['usdc']:.2f}")
            print(f"BTC: {portfolio['crypto']:.8f} (${portfolio['crypto_value']:.2f})")
            print(f"Trades: {len(self.trades_made)}")
            if self.trades_made:
                print(f"\nTrade history:")
                for t in self.trades_made:
                    print(f"   {t['time'].strftime('%H:%M')} - {t['action']} @ ${t['price']:,.2f}")
            print("=" * 70)


def main():
    print("=" * 70)
    print("🤖 SMART ACCUMULATOR BOT v3 - SETUP")
    print("   Now with SENTIMENT ANALYSIS!")
    print("=" * 70)
    
    # Show balances
    print("\n💰 Current Balances:")
    balances = get_all_balances()
    for currency, balance in balances.items():
        print(f"   {currency}: {balance}")
    
    # Quick sentiment preview
    print("\n📊 Quick Sentiment Check...")
    sentiment = get_combined_sentiment()
    fg = sentiment['fear_greed']
    print(f"   {fg['emoji']} Fear & Greed: {fg['value']} ({fg['classification']})")
    print(f"   {sentiment['emoji']} Overall: {sentiment['overall']}")
    
    # Config
    print("\n" + "-" * 70)
    print("Configuration (Enter for defaults):")
    
    target = input("   Target $ (default 100): ").strip() or "100"
    interval = input("   Check interval mins (default 15): ").strip() or "15"
    trade_pct = input("   Trade % per signal (default 50): ").strip() or "50"
    sent_weight = input("   Sentiment weight 0-100% (default 30): ").strip() or "30"
    
    print("\n⚠️  WARNING: Real money trading!")
    confirm = input("   Start bot? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("Cancelled.")
        return
    
    bot = SmartAccumulatorBotV3(
        product_id="BTC-USDC",
        target_value=float(target),
        check_interval_minutes=int(interval),
        trade_percent=float(trade_pct),
        sentiment_weight=float(sent_weight) / 100
    )
    
    bot.run()


if __name__ == "__main__":
    main()
