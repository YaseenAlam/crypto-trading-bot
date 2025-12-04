"""
Crypto Trade Execution Module
Buy and sell crypto through Coinbase Advanced Trade API

⚠️  WARNING: This executes REAL trades with REAL money!
Start with small amounts until you're confident the bot works correctly.
"""

import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

from coinbase_client import get_coinbase_client

load_dotenv()


def get_account_balance(currency: str = "USDC") -> float:
    """
    Get the available balance of a specific currency.
    
    Args:
        currency: Currency code (e.g., 'USDC', 'BTC', 'ETH')
        
    Returns:
        Available balance as float
    """
    client = get_coinbase_client()
    accounts = client.get_accounts()
    
    for acc in accounts.accounts:
        if acc.currency == currency:
            if isinstance(acc.available_balance, dict):
                return float(acc.available_balance['value'])
            else:
                return float(acc.available_balance.value)
    
    return 0.0


def get_all_balances() -> dict:
    """
    Get all non-zero balances.
    
    Returns:
        Dictionary of {currency: balance}
    """
    client = get_coinbase_client()
    accounts = client.get_accounts()
    
    balances = {}
    for acc in accounts.accounts:
        if isinstance(acc.available_balance, dict):
            balance = float(acc.available_balance['value'])
        else:
            balance = float(acc.available_balance.value)
        
        if balance > 0:
            balances[acc.currency] = balance
    
    return balances


def buy_crypto(product_id: str, amount_usd: float) -> dict:
    """
    Buy crypto with a market order.
    
    Args:
        product_id: Trading pair (e.g., 'BTC-USDC')
        amount_usd: Dollar amount to spend
        
    Returns:
        Order response from Coinbase
    """
    client = get_coinbase_client()
    
    # Generate unique order ID
    order_id = str(uuid.uuid4())
    
    # Create market order (buy with quote currency amount)
    order = client.create_order(
        client_order_id=order_id,
        product_id=product_id,
        side="BUY",
        order_configuration={
            "market_market_ioc": {
                "quote_size": str(amount_usd)
            }
        }
    )
    
    # Handle all possible response formats
    oid = "submitted"
    status = "submitted"
    
    try:
        if isinstance(order, dict):
            # Dict response
            if 'success_response' in order:
                sr = order['success_response']
                oid = sr.get('order_id', 'submitted')
                status = sr.get('status', 'submitted')
            else:
                oid = order.get('order_id', 'submitted')
                status = order.get('status', 'submitted')
        elif hasattr(order, 'success_response'):
            # Object with success_response
            sr = order.success_response
            if isinstance(sr, dict):
                oid = sr.get('order_id', 'submitted')
                status = sr.get('status', 'submitted')
            else:
                oid = getattr(sr, 'order_id', 'submitted')
                status = getattr(sr, 'status', 'submitted')
        elif hasattr(order, 'order_id'):
            oid = order.order_id
            status = getattr(order, 'status', 'submitted')
    except:
        pass  # Keep defaults
    
    print(f"✅ BUY ORDER PLACED")
    print(f"   Product: {product_id}")
    print(f"   Amount: ${amount_usd}")
    print(f"   Order ID: {oid}")
    print(f"   Status: {status}")
    
    return order


def sell_crypto(product_id: str, quantity: float) -> dict:
    """
    Sell crypto with a market order.
    
    Args:
        product_id: Trading pair (e.g., 'BTC-USDC')
        quantity: Amount of base currency to sell
        
    Returns:
        Order response from Coinbase
    """
    client = get_coinbase_client()
    
    order_id = str(uuid.uuid4())
    
    order = client.create_order(
        client_order_id=order_id,
        product_id=product_id,
        side="SELL",
        order_configuration={
            "market_market_ioc": {
                "base_size": str(quantity)
            }
        }
    )
    
    # Handle all possible response formats
    oid = "submitted"
    status = "submitted"
    
    try:
        if isinstance(order, dict):
            if 'success_response' in order:
                sr = order['success_response']
                oid = sr.get('order_id', 'submitted')
                status = sr.get('status', 'submitted')
            else:
                oid = order.get('order_id', 'submitted')
                status = order.get('status', 'submitted')
        elif hasattr(order, 'success_response'):
            sr = order.success_response
            if isinstance(sr, dict):
                oid = sr.get('order_id', 'submitted')
                status = sr.get('status', 'submitted')
            else:
                oid = getattr(sr, 'order_id', 'submitted')
                status = getattr(sr, 'status', 'submitted')
        elif hasattr(order, 'order_id'):
            oid = order.order_id
            status = getattr(order, 'status', 'submitted')
    except:
        pass
    
    print(f"✅ SELL ORDER PLACED")
    print(f"   Product: {product_id}")
    print(f"   Quantity: {quantity}")
    print(f"   Order ID: {oid}")
    print(f"   Status: {status}")
    
    return order


def sell_all(product_id: str) -> dict:
    """
    Sell ALL of a specific crypto.
    
    Args:
        product_id: Trading pair (e.g., 'BTC-USDC')
        
    Returns:
        Order response
    """
    base_currency = product_id.split('-')[0]  # e.g., 'BTC' from 'BTC-USDC'
    balance = get_account_balance(base_currency)
    
    if balance <= 0:
        print(f"❌ No {base_currency} to sell")
        return None
    
    return sell_crypto(product_id, balance)


def place_limit_buy(product_id: str, price: float, quantity: float) -> dict:
    """
    Place a limit buy order (only executes at specified price or better).
    
    Args:
        product_id: Trading pair
        price: Maximum price to pay
        quantity: Amount of base currency to buy
        
    Returns:
        Order response
    """
    client = get_coinbase_client()
    order_id = str(uuid.uuid4())
    
    order = client.create_order(
        client_order_id=order_id,
        product_id=product_id,
        side="BUY",
        order_configuration={
            "limit_limit_gtc": {
                "base_size": str(quantity),
                "limit_price": str(price)
            }
        }
    )
    
    print(f"✅ LIMIT BUY ORDER PLACED")
    print(f"   Product: {product_id}")
    print(f"   Price: ${price}")
    print(f"   Quantity: {quantity}")
    
    return order


def place_limit_sell(product_id: str, price: float, quantity: float) -> dict:
    """
    Place a limit sell order (only executes at specified price or better).
    
    Args:
        product_id: Trading pair
        price: Minimum price to accept
        quantity: Amount to sell
        
    Returns:
        Order response
    """
    client = get_coinbase_client()
    order_id = str(uuid.uuid4())
    
    order = client.create_order(
        client_order_id=order_id,
        product_id=product_id,
        side="SELL",
        order_configuration={
            "limit_limit_gtc": {
                "base_size": str(quantity),
                "limit_price": str(price)
            }
        }
    )
    
    print(f"✅ LIMIT SELL ORDER PLACED")
    print(f"   Product: {product_id}")
    print(f"   Price: ${price}")
    print(f"   Quantity: {quantity}")
    
    return order


def get_open_orders(product_id: str = None) -> list:
    """
    Get all open (pending) orders.
    
    Args:
        product_id: Optional filter by trading pair
        
    Returns:
        List of open orders
    """
    client = get_coinbase_client()
    
    if product_id:
        orders = client.list_orders(product_id=product_id, order_status="OPEN")
    else:
        orders = client.list_orders(order_status="OPEN")
    
    if hasattr(orders, 'orders'):
        return orders.orders
    return orders.get('orders', [])


def cancel_order(order_id: str) -> dict:
    """
    Cancel a specific order.
    
    Args:
        order_id: The order ID to cancel
        
    Returns:
        Cancellation response
    """
    client = get_coinbase_client()
    result = client.cancel_orders([order_id])
    
    print(f"✅ Order {order_id} cancelled")
    return result


def cancel_all_orders() -> dict:
    """
    Cancel all open orders.
    
    Returns:
        Cancellation response
    """
    orders = get_open_orders()
    if not orders:
        print("No open orders to cancel")
        return {}
    
    client = get_coinbase_client()
    order_ids = [o.order_id if hasattr(o, 'order_id') else o['order_id'] for o in orders]
    result = client.cancel_orders(order_ids)
    
    print(f"✅ Cancelled {len(order_ids)} orders")
    return result


def get_order_history(limit: int = 10) -> list:
    """
    Get recent order history.
    
    Args:
        limit: Number of orders to fetch
        
    Returns:
        List of recent orders
    """
    client = get_coinbase_client()
    orders = client.list_orders(limit=limit)
    
    if hasattr(orders, 'orders'):
        return orders.orders
    return orders.get('orders', [])


# Main menu when run directly
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 CRYPTO TRADER")
    print("=" * 60)
    
    print("\n💰 Your Balances:")
    print("-" * 40)
    balances = get_all_balances()
    if balances:
        for currency, balance in balances.items():
            print(f"   {currency}: {balance}")
    else:
        print("   No balances found")
    
    print("\n📋 Open Orders:")
    print("-" * 40)
    orders = get_open_orders()
    if orders:
        for order in orders:
            pid = order.product_id if hasattr(order, 'product_id') else order.get('product_id')
            side = order.side if hasattr(order, 'side') else order.get('side')
            print(f"   {pid}: {side}")
    else:
        print("   No open orders")
    
    print("\n" + "=" * 60)
    print("Commands you can use:")
    print("  from trader import buy_crypto, sell_crypto, get_all_balances")
    print("  buy_crypto('BTC-USDC', 5)    # Buy $5 of BTC")
    print("  sell_crypto('BTC-USDC', 0.0001)  # Sell 0.0001 BTC")
    print("  sell_all('BTC-USDC')         # Sell all BTC")
    print("=" * 60)
