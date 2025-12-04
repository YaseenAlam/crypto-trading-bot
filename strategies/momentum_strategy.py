"""
Momentum / Technical Analysis Strategy

Uses RSI, MACD, and moving averages to find buy/sell signals.
More aggressive than DCA - use with caution.
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data_fetcher import get_crypto_data_free, add_technical_indicators
from trader import buy_crypto, sell_crypto, get_account_balance, get_all_balances
from coinbase_client import get_current_price


class MomentumBot:
    """
    Technical Analysis / Momentum Trading Bot
    Uses RSI, MACD, and moving averages to generate signals.
    """
    
    def __init__(
        self,
        product_id: str = "BTC-USDC",
        coin_id: str = "bitcoin",
        trade_amount: float = 10.0,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0
    ):
        self.product_id = product_id
        self.coin_id = coin_id
        self.trade_amount = trade_amount
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.base_currency = product_id.split('-')[0]
        
    def analyze_market(self) -> dict:
        """Fetch data and analyze current market conditions."""
        print(f"📊 Analyzing {self.coin_id}...")
        
        # Get historical data
        df = get_crypto_data_free(self.coin_id, days=30)
        df = add_technical_indicators(df)
        
        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        current_price = latest['close']
        rsi = latest['RSI']
        macd = latest['MACD']
        macd_signal = latest['MACD_Signal']
        sma_7 = latest['SMA_7']
        sma_25 = latest['SMA_25']
        
        # Determine signals
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
        
        # MACD signals
        macd_crossed_up = prev['MACD'] < prev['MACD_Signal'] and macd > macd_signal
        macd_crossed_down = prev['MACD'] > prev['MACD_Signal'] and macd < macd_signal
        
        if macd_crossed_up:
            signals.append("🟢 MACD bullish crossover")
            signal_strength += 1
        elif macd_crossed_down:
            signals.append("🔴 MACD bearish crossover")
            signal_strength -= 1
        elif macd > macd_signal:
            signals.append("⚪ MACD bullish")
        else:
            signals.append("⚪ MACD bearish")
        
        # Moving average signals
        if current_price > sma_25:
            signals.append("🟢 Price above SMA-25 (uptrend)")
            signal_strength += 1
        else:
            signals.append("🔴 Price below SMA-25 (downtrend)")
            signal_strength -= 1
        
        # Determine action
        if signal_strength >= 2:
            action = "BUY"
        elif signal_strength <= -2:
            action = "SELL"
        else:
            action = "HOLD"
        
        return {
            'timestamp': datetime.now().isoformat(),
            'price': round(current_price, 2),
            'rsi': round(rsi, 2),
            'macd': round(macd, 4),
            'macd_signal': round(macd_signal, 4),
            'sma_7': round(sma_7, 2),
            'sma_25': round(sma_25, 2),
            'signals': signals,
            'signal_strength': signal_strength,
            'action': action
        }
    
    def display_analysis(self, analysis: dict):
        """Pretty print the analysis."""
        print("\n" + "=" * 60)
        print(f"📈 MARKET ANALYSIS: {self.product_id}")
        print("=" * 60)
        print(f"Time: {analysis['timestamp']}")
        print(f"Price: ${analysis['price']:,.2f}")
        print(f"\n📊 Indicators:")
        print(f"   RSI: {analysis['rsi']}")
        print(f"   MACD: {analysis['macd']}")
        print(f"   MACD Signal: {analysis['macd_signal']}")
        print(f"   SMA-7: ${analysis['sma_7']:,.2f}")
        print(f"   SMA-25: ${analysis['sma_25']:,.2f}")
        print(f"\n🎯 Signals:")
        for signal in analysis['signals']:
            print(f"   {signal}")
        print(f"\n📍 Signal Strength: {analysis['signal_strength']} / 3")
        print(f"🤖 Recommended Action: {analysis['action']}")
        print("=" * 60)
    
    def execute_signal(self, analysis: dict, dry_run: bool = True) -> dict:
        """Execute trade based on analysis."""
        action = analysis['action']
        
        if action == "HOLD":
            print("⏸️  HOLD - No trade executed")
            return {'action': 'hold'}
        
        if action == "BUY":
            usdc_balance = get_account_balance("USDC")
            
            if usdc_balance < self.trade_amount:
                print(f"❌ Insufficient USDC: ${usdc_balance:.2f} < ${self.trade_amount}")
                return {'action': 'insufficient_funds'}
            
            if dry_run:
                print(f"🔄 [DRY RUN] Would BUY ${self.trade_amount} of {self.product_id}")
                return {'action': 'dry_run_buy'}
            else:
                order = buy_crypto(self.product_id, self.trade_amount)
                return {'action': 'buy', 'order': order}
        
        elif action == "SELL":
            crypto_balance = get_account_balance(self.base_currency)
            
            if crypto_balance <= 0:
                print(f"❌ No {self.base_currency} to sell")
                return {'action': 'nothing_to_sell'}
            
            sell_quantity = min(crypto_balance, self.trade_amount / analysis['price'])
            
            if dry_run:
                print(f"🔄 [DRY RUN] Would SELL {sell_quantity:.8f} {self.base_currency}")
                return {'action': 'dry_run_sell'}
            else:
                order = sell_crypto(self.product_id, sell_quantity)
                return {'action': 'sell', 'order': order}
    
    def backtest(self, days: int = 30) -> dict:
        """Backtest the strategy on historical data."""
        print(f"\n📈 Backtesting {self.coin_id} over {days} days...")
        
        df = get_crypto_data_free(self.coin_id, days=days)
        df = add_technical_indicators(df)
        df = df.dropna()
        
        initial_capital = 1000
        capital = initial_capital
        crypto_held = 0
        trades = []
        
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            
            rsi = row['RSI']
            price = row['close']
            
            macd_crossed_up = prev['MACD'] < prev['MACD_Signal'] and row['MACD'] > row['MACD_Signal']
            macd_crossed_down = prev['MACD'] > prev['MACD_Signal'] and row['MACD'] < row['MACD_Signal']
            
            signal_strength = 0
            if rsi < self.rsi_oversold:
                signal_strength += 1
            elif rsi > self.rsi_overbought:
                signal_strength -= 1
            
            if macd_crossed_up:
                signal_strength += 1
            elif macd_crossed_down:
                signal_strength -= 1
            
            if price > row['SMA_25']:
                signal_strength += 1
            else:
                signal_strength -= 1
            
            if signal_strength >= 2 and capital > 0:
                buy_amount = min(capital, self.trade_amount)
                crypto_bought = buy_amount / price
                crypto_held += crypto_bought
                capital -= buy_amount
                trades.append({'action': 'BUY', 'price': price})
                
            elif signal_strength <= -2 and crypto_held > 0:
                sell_value = crypto_held * price
                capital += sell_value
                trades.append({'action': 'SELL', 'price': price})
                crypto_held = 0
        
        final_value = capital + (crypto_held * df.iloc[-1]['close'])
        
        buy_hold_crypto = initial_capital / df.iloc[0]['close']
        buy_hold_value = buy_hold_crypto * df.iloc[-1]['close']
        
        return {
            'initial_capital': initial_capital,
            'final_value': round(final_value, 2),
            'strategy_return': round((final_value - initial_capital) / initial_capital * 100, 2),
            'buy_hold_value': round(buy_hold_value, 2),
            'buy_hold_return': round((buy_hold_value - initial_capital) / initial_capital * 100, 2),
            'num_trades': len(trades)
        }


def main():
    """Main function with menu."""
    print("=" * 60)
    print("📈 Momentum Trading Bot")
    print("=" * 60)
    
    # Show balances
    print("\n💰 Your Balances:")
    balances = get_all_balances()
    for currency, balance in balances.items():
        print(f"   {currency}: {balance}")
    
    # Create bot
    bot = MomentumBot(
        product_id="BTC-USDC",
        coin_id="bitcoin",
        trade_amount=5.0
    )
    
    print("\n" + "-" * 60)
    print("Options:")
    print("  1. Analyze market")
    print("  2. Analyze + Execute (DRY RUN)")
    print("  3. Analyze + Execute (REAL)")
    print("  4. Run backtest")
    print("  5. Exit")
    
    choice = input("\nChoice: ").strip()
    
    if choice == "1":
        analysis = bot.analyze_market()
        bot.display_analysis(analysis)
        
    elif choice == "2":
        analysis = bot.analyze_market()
        bot.display_analysis(analysis)
        bot.execute_signal(analysis, dry_run=True)
        
    elif choice == "3":
        analysis = bot.analyze_market()
        bot.display_analysis(analysis)
        confirm = input("⚠️  Execute REAL trade? (yes/no): ")
        if confirm.lower() == 'yes':
            bot.execute_signal(analysis, dry_run=False)
        else:
            print("Cancelled.")
            
    elif choice == "4":
        results = bot.backtest(days=30)
        print("\n📊 BACKTEST RESULTS")
        print("=" * 40)
        print(f"Initial Capital: ${results['initial_capital']}")
        print(f"Final Value: ${results['final_value']}")
        print(f"Strategy Return: {results['strategy_return']}%")
        print(f"Buy & Hold Return: {results['buy_hold_return']}%")
        print(f"Number of Trades: {results['num_trades']}")
        
        if results['strategy_return'] > results['buy_hold_return']:
            print("\n✅ Strategy outperformed buy-and-hold!")
        else:
            print("\n❌ Buy-and-hold would have been better")
    else:
        print("Goodbye!")


if __name__ == "__main__":
    main()
