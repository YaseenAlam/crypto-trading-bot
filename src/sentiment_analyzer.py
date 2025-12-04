"""
Crypto Sentiment Analyzer
Scans Reddit, Fear & Greed Index, and news to gauge market sentiment

No API keys needed - uses public data sources
"""

import requests
import re
from datetime import datetime
from collections import Counter


def get_fear_greed_index() -> dict:
    """
    Get the Crypto Fear & Greed Index (0-100).
    0 = Extreme Fear (good time to buy?)
    100 = Extreme Greed (good time to sell?)
    """
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('data'):
            current = data['data'][0]
            value = int(current['value'])
            classification = current['value_classification']
            
            # Convert to signal
            if value <= 25:
                signal = 2  # Extreme fear = strong buy signal
                emoji = "😱"
            elif value <= 40:
                signal = 1  # Fear = mild buy signal
                emoji = "😟"
            elif value <= 60:
                signal = 0  # Neutral
                emoji = "😐"
            elif value <= 75:
                signal = -1  # Greed = mild sell signal
                emoji = "😀"
            else:
                signal = -2  # Extreme greed = strong sell signal
                emoji = "🤑"
            
            return {
                'value': value,
                'classification': classification,
                'signal': signal,
                'emoji': emoji,
                'source': 'Fear & Greed Index'
            }
    except Exception as e:
        print(f"   ⚠️ Fear & Greed fetch failed: {e}")
    
    return {'value': 50, 'classification': 'Neutral', 'signal': 0, 'emoji': '😐', 'source': 'Fear & Greed Index'}


def analyze_reddit_sentiment(subreddit: str = "bitcoin", limit: int = 25) -> dict:
    """
    Analyze sentiment from Reddit posts (no API key needed).
    Uses public JSON feeds.
    """
    try:
        # Reddit public JSON endpoint
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
        headers = {'User-Agent': 'CryptoBot/1.0'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        posts = data.get('data', {}).get('children', [])
        
        if not posts:
            return {'score': 0, 'signal': 0, 'posts_analyzed': 0, 'source': f'r/{subreddit}'}
        
        # Simple keyword-based sentiment
        bullish_words = [
            'moon', 'bullish', 'buy', 'buying', 'long', 'pump', 'rocket', 
            'gains', 'profit', 'ath', 'breakout', 'surge', 'rally', 'hodl',
            'accumulate', 'undervalued', 'cheap', 'dip', 'opportunity',
            'bullrun', 'parabolic', 'lambo', '🚀', '📈', '💎', '🙌'
        ]
        
        bearish_words = [
            'crash', 'bearish', 'sell', 'selling', 'short', 'dump', 'rekt',
            'loss', 'scam', 'dead', 'bubble', 'correction', 'fear', 'panic',
            'overvalued', 'expensive', 'top', 'collapse', 'plunge', 'tank',
            'bloodbath', 'capitulation', '📉', '💀', '🐻'
        ]
        
        bullish_count = 0
        bearish_count = 0
        total_score = 0
        
        for post in posts:
            post_data = post.get('data', {})
            title = post_data.get('title', '').lower()
            score = post_data.get('score', 0)  # Upvotes
            
            # Weight by post popularity
            weight = min(score / 100, 5)  # Cap at 5x weight
            weight = max(weight, 1)
            
            for word in bullish_words:
                if word in title:
                    bullish_count += weight
                    
            for word in bearish_words:
                if word in title:
                    bearish_count += weight
        
        # Calculate sentiment score (-100 to +100)
        total = bullish_count + bearish_count
        if total > 0:
            sentiment_score = ((bullish_count - bearish_count) / total) * 100
        else:
            sentiment_score = 0
        
        # Convert to signal
        if sentiment_score >= 30:
            signal = 1  # Bullish
        elif sentiment_score <= -30:
            signal = -1  # Bearish
        else:
            signal = 0  # Neutral
        
        return {
            'score': round(sentiment_score, 1),
            'signal': signal,
            'bullish_count': round(bullish_count, 1),
            'bearish_count': round(bearish_count, 1),
            'posts_analyzed': len(posts),
            'source': f'r/{subreddit}'
        }
        
    except Exception as e:
        print(f"   ⚠️ Reddit fetch failed: {e}")
        return {'score': 0, 'signal': 0, 'posts_analyzed': 0, 'source': f'r/{subreddit}'}


def analyze_crypto_news() -> dict:
    """
    Analyze recent crypto news headlines.
    Uses CryptoPanic public feed (no API key for basic access).
    """
    try:
        # CryptoPanic public feed
        url = "https://cryptopanic.com/api/v1/posts/?auth_token=free&public=true&kind=news&filter=important&currencies=BTC"
        response = requests.get(url, timeout=10)
        
        # If that fails, try alternative
        if response.status_code != 200:
            return {'score': 0, 'signal': 0, 'headlines': 0, 'source': 'News'}
        
        data = response.json()
        posts = data.get('results', [])[:15]
        
        if not posts:
            return {'score': 0, 'signal': 0, 'headlines': 0, 'source': 'News'}
        
        # Sentiment keywords
        positive_words = [
            'surge', 'rally', 'gain', 'rise', 'jump', 'soar', 'bull', 'record',
            'adoption', 'approve', 'accept', 'partnership', 'launch', 'support',
            'breakout', 'milestone', 'growth', 'buy', 'positive', 'boost'
        ]
        
        negative_words = [
            'crash', 'fall', 'drop', 'plunge', 'bear', 'ban', 'hack', 'scam',
            'fraud', 'lawsuit', 'investigation', 'warning', 'fear', 'sell',
            'collapse', 'reject', 'fail', 'loss', 'negative', 'concern', 'risk'
        ]
        
        positive_count = 0
        negative_count = 0
        
        for post in posts:
            title = post.get('title', '').lower()
            
            for word in positive_words:
                if word in title:
                    positive_count += 1
                    
            for word in negative_words:
                if word in title:
                    negative_count += 1
        
        total = positive_count + negative_count
        if total > 0:
            score = ((positive_count - negative_count) / total) * 100
        else:
            score = 0
        
        if score >= 25:
            signal = 1
        elif score <= -25:
            signal = -1
        else:
            signal = 0
        
        return {
            'score': round(score, 1),
            'signal': signal,
            'positive': positive_count,
            'negative': negative_count,
            'headlines': len(posts),
            'source': 'News'
        }
        
    except Exception as e:
        print(f"   ⚠️ News fetch failed: {e}")
        return {'score': 0, 'signal': 0, 'headlines': 0, 'source': 'News'}


def get_combined_sentiment() -> dict:
    """
    Combine all sentiment sources into one score.
    Returns a signal from -3 (very bearish) to +3 (very bullish).
    """
    print("   📡 Fetching sentiment data...")
    
    # Get all sentiment sources
    fear_greed = get_fear_greed_index()
    reddit_btc = analyze_reddit_sentiment("bitcoin", limit=25)
    reddit_crypto = analyze_reddit_sentiment("cryptocurrency", limit=25)
    news = analyze_crypto_news()
    
    # Combine signals (weighted)
    # Fear & Greed is historically useful, give it more weight
    combined_signal = (
        fear_greed['signal'] * 1.5 +  # Weight: 1.5
        reddit_btc['signal'] * 1.0 +   # Weight: 1.0
        reddit_crypto['signal'] * 0.5 + # Weight: 0.5
        news['signal'] * 1.0            # Weight: 1.0
    )
    
    # Normalize to -3 to +3 scale
    max_possible = 1.5 + 1.0 + 0.5 + 1.0  # = 4
    normalized_signal = (combined_signal / max_possible) * 3
    
    # Determine overall sentiment
    if normalized_signal >= 1.5:
        overall = "VERY BULLISH"
        emoji = "🚀"
    elif normalized_signal >= 0.5:
        overall = "BULLISH"
        emoji = "📈"
    elif normalized_signal <= -1.5:
        overall = "VERY BEARISH"
        emoji = "💀"
    elif normalized_signal <= -0.5:
        overall = "BEARISH"
        emoji = "📉"
    else:
        overall = "NEUTRAL"
        emoji = "😐"
    
    return {
        'combined_signal': round(normalized_signal, 2),
        'overall': overall,
        'emoji': emoji,
        'fear_greed': fear_greed,
        'reddit_bitcoin': reddit_btc,
        'reddit_crypto': reddit_crypto,
        'news': news,
        'timestamp': datetime.now().isoformat()
    }


def display_sentiment(sentiment: dict):
    """Pretty print sentiment analysis."""
    print("\n" + "=" * 60)
    print("📊 SENTIMENT ANALYSIS")
    print("=" * 60)
    
    fg = sentiment['fear_greed']
    print(f"\n{fg['emoji']} Fear & Greed Index: {fg['value']} ({fg['classification']})")
    print(f"   Signal: {'+' if fg['signal'] > 0 else ''}{fg['signal']}")
    
    rb = sentiment['reddit_bitcoin']
    print(f"\n🔥 Reddit r/bitcoin: Score {rb['score']}")
    print(f"   Bullish mentions: {rb['bullish_count']} | Bearish: {rb['bearish_count']}")
    print(f"   Signal: {'+' if rb['signal'] > 0 else ''}{rb['signal']}")
    
    rc = sentiment['reddit_crypto']
    print(f"\n💬 Reddit r/cryptocurrency: Score {rc['score']}")
    print(f"   Bullish mentions: {rc['bullish_count']} | Bearish: {rc['bearish_count']}")
    print(f"   Signal: {'+' if rc['signal'] > 0 else ''}{rc['signal']}")
    
    news = sentiment['news']
    print(f"\n📰 News Headlines: Score {news['score']}")
    print(f"   Positive: {news.get('positive', 0)} | Negative: {news.get('negative', 0)}")
    print(f"   Signal: {'+' if news['signal'] > 0 else ''}{news['signal']}")
    
    print("\n" + "-" * 60)
    print(f"{sentiment['emoji']} OVERALL: {sentiment['overall']}")
    print(f"   Combined Signal: {sentiment['combined_signal']:.2f} (scale: -3 to +3)")
    print("=" * 60)


# Test it
if __name__ == "__main__":
    print("Testing Sentiment Analyzer...\n")
    sentiment = get_combined_sentiment()
    display_sentiment(sentiment)
