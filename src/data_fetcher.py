"""
Crypto Data Fetcher
Gets historical and real-time crypto data for analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

from coinbase_client import get_coinbase_client


def get_historical_candles(product_id: str = "BTC-USDC", granularity: str = "ONE_HOUR", days: int = 7) -> pd.DataFrame:
    """
    Fetch historical candlestick data from Coinbase.
    
    Args:
        product_id: Trading pair (e.g., 'BTC-USDC', 'ETH-USDC')
        granularity: Candle size - 'ONE_MINUTE', 'FIVE_MINUTE', 'FIFTEEN_MINUTE',
                     'THIRTY_MINUTE', 'ONE_HOUR', 'TWO_HOUR', 'SIX_HOUR', 'ONE_DAY'
        days: Number of days of history
        
    Returns:
        DataFrame with OHLCV data
    """
    client = get_coinbase_client()
    
    end = datetime.now()
    start = end - timedelta(days=days)
    
    # Convert to Unix timestamps
    start_ts = int(start.timestamp())
    end_ts = int(end.timestamp())
    
    candles = client.get_candles(
        product_id=product_id,
        start=str(start_ts),
        end=str(end_ts),
        granularity=granularity
    )
    
    # Handle response format
    candle_list = candles.candles if hasattr(candles, 'candles') else candles.get('candles', [])
    
    # Convert to DataFrame
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


def get_crypto_data_free(symbol: str = "bitcoin", days: int = 30) -> pd.DataFrame:
    """
    Fetch crypto data from CoinGecko API (free, no API key needed).
    Great for backtesting and learning.
    
    Args:
        symbol: Coin ID (e.g., 'bitcoin', 'ethereum', 'solana')
        days: Number of days (max 365 for free tier)
        
    Returns:
        DataFrame with price data
    """
    url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': days,
        'interval': 'daily' if days > 1 else 'hourly'
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    # Parse prices
    prices = data.get('prices', [])
    volumes = data.get('total_volumes', [])
    
    df = pd.DataFrame(prices, columns=['timestamp', 'close'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    # Add volume
    vol_df = pd.DataFrame(volumes, columns=['timestamp', 'volume'])
    vol_df['timestamp'] = pd.to_datetime(vol_df['timestamp'], unit='ms')
    vol_df.set_index('timestamp', inplace=True)
    df['volume'] = vol_df['volume']
    
    return df


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add technical indicators for trading signals.
    
    Args:
        df: DataFrame with at least 'close' column
        
    Returns:
        DataFrame with added indicators
    """
    df = df.copy()
    
    # Make sure we have a 'close' column (might be 'Close' or 'close')
    if 'Close' in df.columns:
        df['close'] = df['Close']
    
    # Simple Moving Averages
    df['SMA_7'] = df['close'].rolling(window=7).mean()
    df['SMA_25'] = df['close'].rolling(window=25).mean()
    df['SMA_99'] = df['close'].rolling(window=99).mean()
    
    # Exponential Moving Averages
    df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
    
    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
    
    # RSI (Relative Strength Index)
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
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
    
    # Volatility (standard deviation of returns)
    df['Returns'] = df['close'].pct_change()
    df['Volatility'] = df['Returns'].rolling(window=20).std() * np.sqrt(365)  # Annualized
    
    # Price momentum
    df['Momentum_7'] = df['close'].pct_change(periods=7)
    df['Momentum_14'] = df['close'].pct_change(periods=14)
    
    return df


def get_fear_greed_index() -> dict:
    """
    Get the current Fear & Greed Index for crypto market.
    Useful as a sentiment indicator.
    
    Returns:
        Dictionary with current index value and classification
    """
    url = "https://api.alternative.me/fng/"
    response = requests.get(url)
    data = response.json()
    
    if data.get('data'):
        current = data['data'][0]
        return {
            'value': int(current['value']),
            'classification': current['value_classification'],
            'timestamp': current['timestamp']
        }
    return None


# Quick test
if __name__ == "__main__":
    print("Fetching Bitcoin data from CoinGecko (free)...")
    df = get_crypto_data_free('bitcoin', days=30)
    df = add_technical_indicators(df)
    
    print(f"\n✅ Fetched {len(df)} data points")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    
    print("\n📊 Latest data with indicators:")
    print(df[['close', 'SMA_7', 'SMA_25', 'RSI', 'MACD']].tail())
    
    print("\n😱 Fear & Greed Index:")
    fgi = get_fear_greed_index()
    if fgi:
        print(f"   Value: {fgi['value']} ({fgi['classification']})")
