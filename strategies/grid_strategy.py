"""
Grid Trading Strategy

Grid trading places buy orders below the current price and sell orders
above the current price at regular intervals (a "grid").

Best for: Sideways/ranging markets with volatility
"""

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from trader import (
    place_limit_buy, place_limit_sell, 
    get_open_orders, cancel_all_orders,
    get_account_balance, get_all_balances
)
from coinbase_client import get_current_price


class GridBot:
    """
    Grid Trading Bot
    Places buy orders below current price and sell orders above.
    """
    
    def __init__(
        self,
        product_id: str = "BTC-USDC",
        grid_levels: int = 5,
        grid_spacing_percent: float = 1.0,
        amount_per_grid: float = 10.0
    ):
        self.product_id = product_id
        self.grid_levels = grid_levels
        self.grid_spacing = grid_spacing_percent / 100
        self.amount_per_grid = amount_per_grid
        self.base_currency = product_id.split('-')[0]
        
    def calculate_grid(self, current_price: float) -> dict:
        """Calculate grid levels based on current price."""
        buy_levels = []
        sell_levels = []
        
        for i in range(1, self.grid_levels + 1):
            buy_price = current_price * (1 - self.grid_spacing * i)
            buy_levels.append(round(buy_price, 2))
            
            sell_price = current_price * (1 + self.grid_spacing * i)
            sell_levels.append(round(sell_price, 2))
        
        return {
            'current_price': current_price,
            'buy_levels': buy_levels,
            'sell_levels': sell_levels
        }
    
    def display_grid(self, current_price: float = None):
        """Display the grid visually."""
        if not current_price:
            current_price = get_current_price(self.product_id)
        
        grid = self.calculate_grid(current_price)
        
        print("\n" + "=" * 50)
        print(f"📊 GRID for {self.product_id}")
        print("=" * 50)
        
        # Sell levels (top to bottom)
        for price in reversed(grid['sell_levels']):
            pct_above = ((price / current_price) - 1) * 100
            print(f"  🔴 SELL @ ${price:,.2f}  (+{pct_above:.1f}%)")
        
        print(f"\n  ➡️  CURRENT: ${current_price:,.2f}")
        print()
        
        # Buy levels
        for price in grid['buy_levels']:
            pct_below = (1 - (price / current_price)) * 100
            print(f"  🟢 BUY  @ ${price:,.2f}  (-{pct_below:.1f}%)")
        
        print("=" * 50)
        
        total_buy_capital = self.amount_per_grid * self.grid_levels
        print(f"\n💰 Capital needed for buy orders: ${total_buy_capital:,.2f}")
        
        usdc_balance = get_account_balance("USDC")
        print(f"   Your USDC balance: ${usdc_balance:,.2f}")
        
        if usdc_balance < total_buy_capital:
            print(f"   ⚠️  Need ${total_buy_capital - usdc_balance:.2f} more USDC")
    
    def setup_grid(self, dry_run: bool = True) -> dict:
        """Set up the grid by placing all orders."""
        current_price = get_current_price(self.product_id)
        grid = self.calculate_grid(current_price)
        
        print(f"\n{'='*60}")
        print(f"🤖 Setting up Grid Bot {'(DRY RUN)' if dry_run else '(LIVE)'}")
        print(f"{'='*60}")
        print(f"Product: {self.product_id}")
        print(f"Current Price: ${current_price:,.2f}")
        print(f"Grid Levels: {self.grid_levels} buy + {self.grid_levels} sell")
        print(f"Grid Spacing: {self.grid_spacing * 100}%")
        print(f"Amount per grid: ${self.amount_per_grid}")
        
        orders_placed = []
        
        # Place buy orders
        print(f"\n🟢 Placing BUY orders...")
        for price in grid['buy_levels']:
            quantity = self.amount_per_grid / price
            
            if dry_run:
                print(f"   Would BUY {quantity:.8f} {self.base_currency} @ ${price:,.2f}")
            else:
                try:
                    order = place_limit_buy(self.product_id, price, quantity)
                    orders_placed.append({'side': 'buy', 'price': price})
                except Exception as e:
                    print(f"   ❌ Failed to place buy @ ${price}: {e}")
        
        # Place sell orders (only if we have crypto)
        crypto_balance = get_account_balance(self.base_currency)
        print(f"\n🔴 Placing SELL orders...")
        print(f"   {self.base_currency} balance: {crypto_balance}")
        
        if crypto_balance > 0:
            sell_quantity_each = crypto_balance / self.grid_levels
            
            for price in grid['sell_levels']:
                if dry_run:
                    print(f"   Would SELL {sell_quantity_each:.8f} {self.base_currency} @ ${price:,.2f}")
                else:
                    try:
                        order = place_limit_sell(self.product_id, price, sell_quantity_each)
                        orders_placed.append({'side': 'sell', 'price': price})
                    except Exception as e:
                        print(f"   ❌ Failed to place sell @ ${price}: {e}")
        else:
            print(f"   No {self.base_currency} to sell - skipping sell orders")
        
        print(f"\n✅ Grid setup complete!")
        return {'orders_placed': len(orders_placed), 'grid': grid}


def main():
    """Main function with menu."""
    print("=" * 60)
    print("📊 Grid Trading Bot")
    print("=" * 60)
    
    # Show balances
    print("\n💰 Your Balances:")
    balances = get_all_balances()
    for currency, balance in balances.items():
        print(f"   {currency}: {balance}")
    
    # Get settings
    print("\n" + "-" * 60)
    product = input("Trading pair (default BTC-USDC): ").strip() or "BTC-USDC"
    levels = input("Grid levels (default 5): ").strip() or "5"
    spacing = input("Grid spacing % (default 1.0): ").strip() or "1.0"
    amount = input("Amount per grid $ (default 10): ").strip() or "10"
    
    bot = GridBot(
        product_id=product,
        grid_levels=int(levels),
        grid_spacing_percent=float(spacing),
        amount_per_grid=float(amount)
    )
    
    # Display grid
    bot.display_grid()
    
    print("\n" + "-" * 60)
    print("Options:")
    print("  1. Setup grid (REAL orders)")
    print("  2. Dry run (simulate)")
    print("  3. Cancel all orders")
    print("  4. Exit")
    
    choice = input("\nChoice: ").strip()
    
    if choice == "1":
        confirm = input("⚠️  This will place REAL orders. Confirm? (yes/no): ")
        if confirm.lower() == 'yes':
            bot.setup_grid(dry_run=False)
        else:
            print("Cancelled.")
    elif choice == "2":
        bot.setup_grid(dry_run=True)
    elif choice == "3":
        cancel_all_orders()
    else:
        print("Goodbye!")


if __name__ == "__main__":
    main()
