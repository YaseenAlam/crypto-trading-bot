"""
Coinbase Advanced Trade API Client
Handles authentication and provides access to the trading API
"""

import os
from dotenv import load_dotenv
from coinbase.rest import RESTClient

# Load environment variables
load_dotenv()


def get_coinbase_client():
    """
    Creates and returns an authenticated Coinbase Advanced Trade client.
    Make sure your .env file has the API keys set.
    """
    api_key = os.getenv('COINBASE_API_KEY')
    api_secret = os.getenv('COINBASE_API_SECRET')
    
    if not api_key or not api_secret:
        raise ValueError(
            "Missing API keys! Make sure you've:\n"
            "1. Copied .env.example to .env\n"
            "2. Added your Coinbase API keys to .env"
        )
    
    # Handle the newline characters in the private key
    api_secret = api_secret.replace('\\n', '\n')
    
    client = RESTClient(api_key=api_key, api_secret=api_secret)
    return client


def check_connection():
    """
    Tests the API connection and prints account info.
    Run this first to make sure everything is working.
    """
    try:
        client = get_coinbase_client()
        
        # Get accounts
        accounts = client.get_accounts()
        
        print("=" * 60)
        print("✅ CONNECTION SUCCESSFUL!")
        print("=" * 60)
        
        # Show balances for accounts with money
        print("\n💰 Your Balances:")
        print("-" * 40)
        
        total_usd_value = 0
        account_list = accounts.accounts if hasattr(accounts, 'accounts') else accounts.get('accounts', [])
        
        for account in account_list:
            # Handle both object and dict formats
            try:
                if isinstance(account.available_balance, dict):
                    balance = float(account.available_balance['value'])
                else:
                    balance = float(account.available_balance.value)
                currency = account.currency
            except:
                balance = float(account.get('available_balance', {}).get('value', 0))
                currency = account.get('currency', 'Unknown')
            
            if balance > 0:
                print(f"  {currency}: {balance:.8f}")
                
                # Rough USD estimate for major coins
                if currency == 'USD' or currency == 'USDC':
                    total_usd_value += balance
        
        print("-" * 40)
        print(f"  Estimated USD Value: ${total_usd_value:,.2f}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print("=" * 60)
        print("❌ CONNECTION FAILED!")
        print("=" * 60)
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your API key and secret in .env")
        print("2. Make sure the private key includes the BEGIN/END lines")
        print("3. Ensure your API key has 'Trade' permissions")
        print("=" * 60)
        return False


def get_current_price(product_id: str = "BTC-USDC") -> float:
    """
    Get the current price of a trading pair.
    
    Args:
        product_id: Trading pair (e.g., 'BTC-USDC', 'ETH-USDC')
        
    Returns:
        Current price as float
    """
    client = get_coinbase_client()
    
    # Get product info
    product = client.get_product(product_id)
    
    if hasattr(product, 'price'):
        price = float(product.price)
    else:
        price = float(product.get('price', 0))
    
    return price


def list_available_products():
    """
    List all available trading pairs on Coinbase.
    """
    client = get_coinbase_client()
    products = client.get_products()
    
    # Handle both object and dict formats
    product_list = products.products if hasattr(products, 'products') else products.get('products', [])
    
    # Filter for USDC pairs (most common for trading)
    usdc_pairs = []
    for product in product_list:
        if hasattr(product, 'product_id'):
            product_id = product.product_id
            base = product.base_currency_id
            quote = product.quote_currency_id
            status = product.status
        else:
            product_id = product.get('product_id', '')
            base = product.get('base_currency_id')
            quote = product.get('quote_currency_id')
            status = product.get('status')
            
        if 'USDC' in product_id:
            usdc_pairs.append({
                'id': product_id,
                'base': base,
                'quote': quote,
                'status': status
            })
    
    return usdc_pairs


if __name__ == "__main__":
    check_connection()
