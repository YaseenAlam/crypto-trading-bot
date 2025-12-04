"""
Trading Brain - Memory & Learning System

This gives the bot:
- Memory of all trades and their outcomes
- Performance tracking (win rate, profit/loss)
- Adaptive behavior based on what's working
- Risk management (stop trading if losing too much)
- Reasoning/journaling for each decision
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional


class TradingBrain:
    """
    The bot's memory and decision-making center.
    Tracks history, learns from outcomes, manages risk.
    """
    
    def __init__(self, memory_file: str = "trading_memory.json"):
        self.memory_file = memory_file
        self.memory = self._load_memory()
        
    def _load_memory(self) -> dict:
        """Load memory from file or create new."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Fresh memory structure
        return {
            'trades': [],
            'decisions': [],
            'daily_stats': {},
            'settings': {
                'max_daily_loss_percent': 10,
                'max_consecutive_losses': 3,
                'min_confidence_to_trade': 50,
                'learned_adjustments': {}
            },
            'created': datetime.now().isoformat(),
            'total_starting_value': 0
        }
    
    def save(self):
        """Save memory to file."""
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2, default=str)
    
    def set_starting_value(self, value: float):
        """Set the initial portfolio value for tracking."""
        if self.memory['total_starting_value'] == 0:
            self.memory['total_starting_value'] = value
            self.save()
    
    # ========== TRADE TRACKING ==========
    
    def record_trade(self, action: str, amount: float, price: float, 
                     reasoning: str, signals: dict) -> dict:
        """Record a trade with full context."""
        trade = {
            'id': len(self.memory['trades']) + 1,
            'timestamp': datetime.now().isoformat(),
            'action': action,  # BUY or SELL
            'amount': amount,
            'price': price,
            'reasoning': reasoning,
            'signals': signals,
            'outcome': None,  # Filled later when we know if it was good
            'profit_loss': None
        }
        
        self.memory['trades'].append(trade)
        self.save()
        return trade
    
    def get_open_position(self) -> Optional[dict]:
        """Get the last BUY that hasn't been SOLD."""
        buys = [t for t in self.memory['trades'] if t['action'] == 'BUY']
        sells = [t for t in self.memory['trades'] if t['action'] == 'SELL']
        
        if len(buys) > len(sells):
            return buys[-1]
        return None
    
    def calculate_trade_outcome(self, current_price: float):
        """Update outcomes for past trades based on current price."""
        open_position = self.get_open_position()
        
        if open_position and open_position['outcome'] is None:
            buy_price = open_position['price']
            pct_change = ((current_price - buy_price) / buy_price) * 100
            
            # Update the trade
            open_position['current_price'] = current_price
            open_position['unrealized_pct'] = round(pct_change, 2)
            self.save()
    
    def close_position(self, sell_price: float, amount: float):
        """Mark a position as closed and calculate profit/loss."""
        open_position = self.get_open_position()
        
        if open_position:
            buy_price = open_position['price']
            pct_change = ((sell_price - buy_price) / buy_price) * 100
            
            open_position['outcome'] = 'WIN' if pct_change > 0 else 'LOSS'
            open_position['profit_loss_pct'] = round(pct_change, 2)
            open_position['closed_at'] = datetime.now().isoformat()
            open_position['sell_price'] = sell_price
            
            self.save()
            return open_position
        return None
    
    # ========== PERFORMANCE STATS ==========
    
    def get_performance_stats(self) -> dict:
        """Calculate overall trading performance."""
        trades = self.memory['trades']
        closed_trades = [t for t in trades if t.get('outcome') is not None]
        
        if not closed_trades:
            return {
                'total_trades': len(trades),
                'closed_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'best_trade': 0,
                'worst_trade': 0,
                'consecutive_losses': 0
            }
        
        wins = [t for t in closed_trades if t['outcome'] == 'WIN']
        losses = [t for t in closed_trades if t['outcome'] == 'LOSS']
        
        win_rate = (len(wins) / len(closed_trades)) * 100 if closed_trades else 0
        
        avg_profit = sum(t['profit_loss_pct'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['profit_loss_pct'] for t in losses) / len(losses) if losses else 0
        
        all_pcts = [t['profit_loss_pct'] for t in closed_trades]
        best = max(all_pcts) if all_pcts else 0
        worst = min(all_pcts) if all_pcts else 0
        
        # Count consecutive losses at the end
        consecutive_losses = 0
        for t in reversed(closed_trades):
            if t['outcome'] == 'LOSS':
                consecutive_losses += 1
            else:
                break
        
        return {
            'total_trades': len(trades),
            'closed_trades': len(closed_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': round(win_rate, 1),
            'avg_profit': round(avg_profit, 2),
            'avg_loss': round(avg_loss, 2),
            'best_trade': round(best, 2),
            'worst_trade': round(worst, 2),
            'consecutive_losses': consecutive_losses
        }
    
    def get_today_stats(self) -> dict:
        """Get today's trading performance."""
        today = datetime.now().date().isoformat()
        today_trades = [
            t for t in self.memory['trades']
            if t['timestamp'].startswith(today)
        ]
        
        if not today_trades:
            return {'trades': 0, 'profit_loss': 0}
        
        closed_today = [t for t in today_trades if t.get('profit_loss_pct') is not None]
        total_pnl = sum(t['profit_loss_pct'] for t in closed_today)
        
        return {
            'trades': len(today_trades),
            'closed': len(closed_today),
            'profit_loss_pct': round(total_pnl, 2)
        }
    
    # ========== RISK MANAGEMENT ==========
    
    def should_stop_trading(self, current_value: float) -> tuple:
        """
        Check if we should stop trading due to risk limits.
        Returns (should_stop, reason)
        """
        settings = self.memory['settings']
        stats = self.get_performance_stats()
        today = self.get_today_stats()
        
        # Check consecutive losses
        if stats['consecutive_losses'] >= settings['max_consecutive_losses']:
            return True, f"Hit {stats['consecutive_losses']} consecutive losses. Taking a break."
        
        # Check daily loss limit
        starting = self.memory['total_starting_value']
        if starting > 0:
            total_change = ((current_value - starting) / starting) * 100
            if total_change <= -settings['max_daily_loss_percent']:
                return True, f"Down {abs(total_change):.1f}% from start. Stopping to prevent further losses."
        
        return False, None
    
    # ========== DECISION MAKING ==========
    
    def record_decision(self, action: str, reasoning: str, 
                        tech_signal: float, sent_signal: float,
                        final_signal: float, confidence: float):
        """Record a decision (including HOLDs) with reasoning."""
        decision = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'reasoning': reasoning,
            'tech_signal': tech_signal,
            'sent_signal': sent_signal,
            'final_signal': final_signal,
            'confidence': confidence
        }
        
        self.memory['decisions'].append(decision)
        
        # Keep last 100 decisions only
        if len(self.memory['decisions']) > 100:
            self.memory['decisions'] = self.memory['decisions'][-100:]
        
        self.save()
    
    def generate_reasoning(self, action: str, tech_data: dict, 
                           sent_data: dict, portfolio: dict) -> str:
        """Generate human-like reasoning for a decision."""
        
        stats = self.get_performance_stats()
        open_pos = self.get_open_position()
        
        reasons = []
        
        # Current position context
        if open_pos:
            buy_price = open_pos['price']
            current_price = portfolio['price']
            pct = ((current_price - buy_price) / buy_price) * 100
            
            if pct > 0:
                reasons.append(f"Currently holding BTC bought at ${buy_price:,.0f}, now up {pct:.1f}%.")
            else:
                reasons.append(f"Currently holding BTC bought at ${buy_price:,.0f}, now down {abs(pct):.1f}%.")
        else:
            reasons.append("Not currently holding any BTC position.")
        
        # Technical context
        rsi = tech_data.get('rsi', 50)
        if rsi < 35:
            reasons.append(f"RSI at {rsi:.0f} indicates oversold conditions - potential buying opportunity.")
        elif rsi > 65:
            reasons.append(f"RSI at {rsi:.0f} indicates overbought conditions - caution advised.")
        else:
            reasons.append(f"RSI at {rsi:.0f} is neutral.")
        
        # Sentiment context
        overall = sent_data.get('overall', 'NEUTRAL')
        fg = sent_data.get('fear_greed', {}).get('value', 50)
        
        if fg < 30:
            reasons.append(f"Market sentiment shows extreme fear (F&G: {fg}) - historically a good time to buy.")
        elif fg > 70:
            reasons.append(f"Market sentiment shows extreme greed (F&G: {fg}) - historically risky to buy.")
        
        # Past performance context
        if stats['closed_trades'] > 0:
            reasons.append(f"Track record: {stats['win_rate']:.0f}% win rate over {stats['closed_trades']} trades.")
            
            if stats['consecutive_losses'] >= 2:
                reasons.append(f"Warning: {stats['consecutive_losses']} losses in a row - being cautious.")
        
        # Action reasoning
        if action == "BUY":
            reasons.append("DECISION: Signals align for a buy. Executing purchase.")
        elif action == "SELL":
            reasons.append("DECISION: Signals suggest taking profits or cutting losses.")
        else:
            reasons.append("DECISION: Mixed signals - holding current position until clearer opportunity.")
        
        return " ".join(reasons)
    
    def get_adaptive_thresholds(self) -> dict:
        """
        Adjust trading thresholds based on what's been working.
        If our buys at RSI < 30 have been losing, maybe try RSI < 25.
        """
        stats = self.get_performance_stats()
        
        # Default thresholds
        thresholds = {
            'rsi_oversold': 35,
            'rsi_overbought': 65,
            'min_signal_strength': 1.0
        }
        
        # If we're losing a lot, be more conservative
        if stats['consecutive_losses'] >= 2:
            thresholds['rsi_oversold'] = 30  # Require more oversold
            thresholds['min_signal_strength'] = 1.5  # Require stronger signal
        
        if stats['win_rate'] < 40 and stats['closed_trades'] >= 5:
            thresholds['rsi_oversold'] = 28
            thresholds['rsi_overbought'] = 72
            thresholds['min_signal_strength'] = 1.8
        
        return thresholds
    
    # ========== DISPLAY ==========
    
    def display_memory_status(self):
        """Show what the brain knows."""
        stats = self.get_performance_stats()
        today = self.get_today_stats()
        open_pos = self.get_open_position()
        
        print("\n" + "=" * 50)
        print("🧠 TRADING BRAIN STATUS")
        print("=" * 50)
        
        print(f"\n📊 Performance:")
        print(f"   Total trades: {stats['total_trades']}")
        print(f"   Closed trades: {stats['closed_trades']}")
        if stats['closed_trades'] > 0:
            print(f"   Win rate: {stats['win_rate']}%")
            print(f"   Best trade: +{stats['best_trade']}%")
            print(f"   Worst trade: {stats['worst_trade']}%")
            print(f"   Consecutive losses: {stats['consecutive_losses']}")
        
        print(f"\n📅 Today:")
        print(f"   Trades: {today['trades']}")
        print(f"   P/L: {today['profit_loss_pct']:+.2f}%")
        
        if open_pos:
            print(f"\n📍 Open Position:")
            print(f"   Bought at: ${open_pos['price']:,.2f}")
            print(f"   Time: {open_pos['timestamp']}")
            if 'unrealized_pct' in open_pos:
                print(f"   Unrealized: {open_pos['unrealized_pct']:+.2f}%")
        else:
            print(f"\n📍 No open position")
        
        thresholds = self.get_adaptive_thresholds()
        print(f"\n🎚️ Adaptive Thresholds:")
        print(f"   RSI Buy below: {thresholds['rsi_oversold']}")
        print(f"   RSI Sell above: {thresholds['rsi_overbought']}")
        print(f"   Min signal: {thresholds['min_signal_strength']}")
        
        print("=" * 50)


# Test
if __name__ == "__main__":
    brain = TradingBrain("test_memory.json")
    brain.set_starting_value(25.0)
    
    # Simulate some trades
    brain.record_trade(
        action="BUY",
        amount=10,
        price=95000,
        reasoning="RSI oversold, sentiment fearful",
        signals={'rsi': 28, 'sentiment': 'fear'}
    )
    
    brain.display_memory_status()
    
    # Clean up test file
    if os.path.exists("test_memory.json"):
        os.remove("test_memory.json")
