"""
DCA (Dollar Cost Averaging) Strategy

This is the SAFEST strategy for beginners. Instead of trying to time the market,
you invest a fixed amount at regular intervals regardless of price.

Why DCA works:
- When prices are high, you buy less crypto
- When prices are low, you buy more crypto
- Over time, this averages out to a good entry price
- Removes emotion from trading
"""

import os
import sys
import json
import time
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from trader import buy_crypto, get_account_balance, get_all_balances
from coinbase_client import get_current_price


class DCABot:
    """
    Dollar Cost Averaging Bot
    Automatically buys a fixed amount of crypto at regular intervals.
    """
    
    def __init__(
        self,
        product_id: str = "BTC-USDC",
        amount_per_buy: float = 10.0,
        log_file: str = "dca_log.json"
    ):
        self.product_id = product_id
        self.amount_per_buy = amount_per_buy
        self.log_file = log_file
        self.base_currency = product_id.split('-')[0]
        self.transactions = self._load_log()
        
    def _load_log(self) -> list:
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_log(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.transactions, f, indent=2, default=str)
    
    def execute_buy(self, dry_run: bool = False) -> dict:
        """Execute a single DCA buy."""
        
        # Check USDC balance
        usdc_balance = get_account_balance("USDC")
        
        if usdc_balance < self.amount_per_buy:
            print(f"❌ Insufficient USDC balance: ${usdc_balance:.2f}")
            print(f"   Need: ${self.amount_per_buy:.2f}")
            return None
        
        # Get current price
        try:
            current_price = get_current_price(self.product_id)
        except:
            current_price = 0
        
        transaction = {
            'timestamp': datetime.now().isoformat(),
            'product': self.product_id,
            'amount_usd': self.amount_per_buy,
            'price_at_buy': current_price,
            'status': 'pending'
        }
        
        if dry_run:
            print(f"🔄 [DRY RUN] Would buy ${self.amount_per_buy} of {self.product_id}")
            print(f"   Current price: ${current_price:,.2f}")
            if current_price > 0:
                print(f"   Estimated {self.base_currency}: {self.amount_per_buy / current_price:.8f}")
            transaction['status'] = 'dry_run'
        else:
            print(f"\n{'='*50}")
            print(f"🤖 DCA Bot Executing Buy")
            print(f"{'='*50}")
            print(f"Time: {datetime.now()}")
            print(f"Product: {self.product_id}")
            print(f"Amount: ${self.amount_per_buy}")
            print(f"Current Price: ${current_price:,.2f}")
            
            try:
                order = buy_crypto(self.product_id, self.amount_per_buy)
                transaction['status'] = 'completed'
                print(f"✅ Buy executed successfully!")
            except Exception as e:
                transaction['status'] = 'failed'
                transaction['error'] = str(e)
                print(f"❌ Buy failed: {e}")
        
        self.transactions.append(transaction)
        self._save_log()
        
        return transaction
    
    def get_stats(self) -> dict:
        """Calculate DCA statistics."""
        if not self.transactions:
            return {'message': 'No transactions yet'}
        
        successful = [t for t in self.transactions if t['status'] not in ['failed', 'dry_run']]
        
        if not successful:
            return {'message': 'No successful transactions yet'}
        
        total_invested = sum(t['amount_usd'] for t in successful)
        
        prices = [t['price_at_buy'] for t in successful if t.get('price_at_buy', 0) > 0]
        avg_price = sum(prices) / len(prices) if prices else 0
        
        try:
            current_price = get_current_price(self.product_id)
        except:
            current_price = avg_price
        
        estimated_crypto = sum(t['amount_usd'] / t['price_at_buy'] 
                              for t in successful 
                              if t.get('price_at_buy', 0) > 0)
        current_value = estimated_crypto * current_price
        
        profit_loss = current_value - total_invested
        profit_loss_pct = (profit_loss / total_invested * 100) if total_invested > 0 else 0
        
        return {
            'total_buys': len(successful),
            'total_invested': round(total_invested, 2),
            'average_buy_price': round(avg_price, 2),
            'current_price': round(current_price, 2),
            'estimated_holdings': round(estimated_crypto, 8),
            'current_value': round(current_value, 2),
            'profit_loss': round(profit_loss, 2),
            'profit_loss_percent': round(profit_loss_pct, 2)
        }


def main():
    """Main function with menu."""
    print("=" * 60)
    print("🤖 DCA (Dollar Cost Averaging) Bot")
    print("=" * 60)
    
    # Show current balances
    print("\n💰 Your Balances:")
    balances = get_all_balances()
    for currency, balance in balances.items():
        print(f"   {currency}: {balance}")
    
    # Get user input
    print("\n" + "-" * 60)
    product = input("Enter trading pair (default BTC-USDC): ").strip() or "BTC-USDC"
    amount = input("Enter amount per buy in USD (default 5): ").strip() or "5"
    
    try:
        amount = float(amount)
    except:
        amount = 5.0
    
    bot = DCABot(product_id=product, amount_per_buy=amount)
    
    print(f"\n📊 Current {product} price: ${get_current_price(product):,.2f}")
    
    print("\n" + "-" * 60)
    print("Options:")
    print("  1. Execute buy (REAL)")
    print("  2. Dry run (simulate)")
    print("  3. View stats")
    print("  4. Exit")
    
    choice = input("\nChoice: ").strip()
    
    if choice == "1":
        confirm = input(f"⚠️  This will spend ${amount} USDC. Confirm? (yes/no): ")
        if confirm.lower() == 'yes':
            bot.execute_buy(dry_run=False)
        else:
            print("Cancelled.")
    elif choice == "2":
        bot.execute_buy(dry_run=True)
    elif choice == "3":
        stats = bot.get_stats()
        print("\n📈 DCA Stats:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
    else:
        print("Goodbye!")


if __name__ == "__main__":
    main()
