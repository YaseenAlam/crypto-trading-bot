"""
Advanced Crypto Sentiment Analyzer with NLP

Uses actual Natural Language Processing (transformer models) to understand
context, sarcasm, and meaning - not just keyword counting.

Models used:
- FinBERT: Fine-tuned for financial sentiment
- Fallback: TextBlob for basic sentiment if transformers unavailable
"""

import os
import sys
import requests
from datetime import datetime
from typing import List, Dict, Tuple

# Try to import NLP libraries
NLP_AVAILABLE = False
FINBERT_AVAILABLE = False

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    NLP_AVAILABLE = True
    
    # Check if FinBERT can be loaded
    try:
        # This will be loaded lazily
        FINBERT_AVAILABLE = True
    except:
        pass
except ImportError:
    pass

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False


class NLPSentimentAnalyzer:
    """
    Advanced sentiment analyzer using transformer models.
    """
    
    def __init__(self, use_finbert: bool = True):
        self.model_loaded = False
        self.sentiment_pipeline = None
        self.use_finbert = use_finbert
        
        if NLP_AVAILABLE:
            self._load_model()
        else:
            print("⚠️  Transformers not installed. Using fallback sentiment analysis.")
            print("   Install with: pip install transformers torch")
    
    def _load_model(self):
        """Load the NLP model."""
        try:
            print("🧠 Loading NLP model (first time may take a minute)...")
            
            if self.use_finbert:
                # FinBERT - specifically trained on financial text
                model_name = "ProsusAI/finbert"
            else:
                # General sentiment model
                model_name = "cardiffnlp/twitter-roberta-base-sentiment-latest"
            
            self.sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model=model_name,
                tokenizer=model_name,
                top_k=None,  # Return all scores
                truncation=True,
                max_length=512
            )
            
            self.model_loaded = True
            print(f"✅ NLP Model loaded: {model_name}")
            
        except Exception as e:
            print(f"⚠️  Could not load transformer model: {e}")
            print("   Using fallback sentiment analysis.")
            self.model_loaded = False
    
    def analyze_text(self, text: str) -> Dict:
        """
        Analyze sentiment of a single text.
        Returns score from -1 (bearish) to +1 (bullish)
        """
        if not text or len(text.strip()) < 3:
            return {'score': 0, 'label': 'neutral', 'confidence': 0}
        
        try:
            if self.model_loaded and self.sentiment_pipeline:
                # Use transformer model
                result = self.sentiment_pipeline(text[:512])[0]  # Truncate to max length
                
                # FinBERT returns: positive, negative, neutral
                scores = {r['label'].lower(): r['score'] for r in result}
                
                # Convert to single score: -1 to +1
                positive = scores.get('positive', 0)
                negative = scores.get('negative', 0)
                neutral = scores.get('neutral', 0)
                
                # Weighted score
                score = positive - negative
                
                # Determine label
                if positive > negative and positive > neutral:
                    label = 'bullish'
                elif negative > positive and negative > neutral:
                    label = 'bearish'
                else:
                    label = 'neutral'
                
                confidence = max(positive, negative, neutral)
                
                return {
                    'score': round(score, 3),
                    'label': label,
                    'confidence': round(confidence, 3),
                    'positive': round(positive, 3),
                    'negative': round(negative, 3),
                    'neutral': round(neutral, 3)
                }
            
            elif TEXTBLOB_AVAILABLE:
                # Fallback to TextBlob
                blob = TextBlob(text)
                polarity = blob.sentiment.polarity  # -1 to +1
                
                if polarity > 0.1:
                    label = 'bullish'
                elif polarity < -0.1:
                    label = 'bearish'
                else:
                    label = 'neutral'
                
                return {
                    'score': round(polarity, 3),
                    'label': label,
                    'confidence': abs(polarity)
                }
            
            else:
                # Last resort: keyword-based
                return self._keyword_fallback(text)
                
        except Exception as e:
            return {'score': 0, 'label': 'neutral', 'confidence': 0, 'error': str(e)}
    
    def _keyword_fallback(self, text: str) -> Dict:
        """Keyword-based fallback if no NLP available."""
        text_lower = text.lower()
        
        bullish = ['moon', 'bullish', 'buy', 'pump', 'rocket', 'gains', 'profit',
                   'surge', 'rally', 'breakout', 'hodl', 'accumulate', 'undervalued']
        bearish = ['crash', 'bearish', 'sell', 'dump', 'rekt', 'scam', 'dead',
                   'bubble', 'collapse', 'panic', 'fear', 'drop', 'plunge']
        
        bull_count = sum(1 for word in bullish if word in text_lower)
        bear_count = sum(1 for word in bearish if word in text_lower)
        
        total = bull_count + bear_count
        if total == 0:
            return {'score': 0, 'label': 'neutral', 'confidence': 0}
        
        score = (bull_count - bear_count) / total
        label = 'bullish' if score > 0 else 'bearish' if score < 0 else 'neutral'
        
        return {'score': round(score, 3), 'label': label, 'confidence': abs(score)}
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """Analyze multiple texts efficiently."""
        return [self.analyze_text(t) for t in texts]
    
    def get_aggregate_sentiment(self, texts: List[str], weights: List[float] = None) -> Dict:
        """
        Analyze multiple texts and return weighted aggregate sentiment.
        
        Args:
            texts: List of texts to analyze
            weights: Optional weights for each text (e.g., by upvotes)
        """
        if not texts:
            return {'score': 0, 'label': 'neutral', 'count': 0}
        
        if weights is None:
            weights = [1.0] * len(texts)
        
        results = self.analyze_batch(texts)
        
        total_weight = sum(weights)
        weighted_score = sum(r['score'] * w for r, w in zip(results, weights))
        avg_score = weighted_score / total_weight if total_weight > 0 else 0
        
        # Count sentiments
        bullish_count = sum(1 for r in results if r['label'] == 'bullish')
        bearish_count = sum(1 for r in results if r['label'] == 'bearish')
        neutral_count = sum(1 for r in results if r['label'] == 'neutral')
        
        # Overall label
        if avg_score > 0.15:
            label = 'bullish'
        elif avg_score < -0.15:
            label = 'bearish'
        else:
            label = 'neutral'
        
        return {
            'score': round(avg_score, 3),
            'label': label,
            'count': len(texts),
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'neutral_count': neutral_count,
            'model': 'FinBERT' if self.model_loaded else 'Fallback'
        }


# ============== DATA FETCHERS ==============

def get_fear_greed_index() -> Dict:
    """Get the Crypto Fear & Greed Index."""
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('data'):
            current = data['data'][0]
            value = int(current['value'])
            classification = current['value_classification']
            
            if value <= 25:
                signal = 2
                emoji = "😱"
            elif value <= 40:
                signal = 1
                emoji = "😟"
            elif value <= 60:
                signal = 0
                emoji = "😐"
            elif value <= 75:
                signal = -1
                emoji = "😀"
            else:
                signal = -2
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
    
    return {'value': 50, 'classification': 'Neutral', 'signal': 0, 'emoji': '😐'}


def get_reddit_posts(subreddit: str = "bitcoin", limit: int = 25) -> List[Dict]:
    """Fetch Reddit posts with metadata."""
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
        headers = {'User-Agent': 'CryptoBot/2.0 NLP'}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        posts = data.get('data', {}).get('children', [])
        
        results = []
        for post in posts:
            p = post.get('data', {})
            results.append({
                'title': p.get('title', ''),
                'score': p.get('score', 0),
                'num_comments': p.get('num_comments', 0),
                'upvote_ratio': p.get('upvote_ratio', 0.5),
                'created': p.get('created_utc', 0)
            })
        
        return results
        
    except Exception as e:
        print(f"   ⚠️ Reddit fetch failed: {e}")
        return []


def get_crypto_news() -> List[Dict]:
    """Fetch crypto news headlines."""
    try:
        # Try CoinGecko news (no API key needed)
        url = "https://api.coingecko.com/api/v3/news"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            news = response.json().get('data', [])[:20]
            return [{'title': n.get('title', ''), 'source': n.get('author', '')} for n in news]
    except:
        pass
    
    try:
        # Fallback to Cryptopanic
        url = "https://cryptopanic.com/api/v1/posts/?auth_token=free&public=true&kind=news"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            posts = response.json().get('results', [])[:20]
            return [{'title': p.get('title', ''), 'source': p.get('source', {}).get('title', '')} for p in posts]
    except:
        pass
    
    return []


# ============== MAIN ANALYZER ==============

class AdvancedSentimentAnalyzer:
    """
    Complete sentiment analysis system using NLP.
    """
    
    def __init__(self):
        print("=" * 60)
        print("🧠 ADVANCED SENTIMENT ANALYZER (NLP)")
        print("=" * 60)
        self.nlp = NLPSentimentAnalyzer(use_finbert=True)
    
    def analyze_reddit(self, subreddit: str = "bitcoin") -> Dict:
        """Analyze Reddit sentiment using NLP."""
        print(f"   📡 Fetching r/{subreddit}...")
        posts = get_reddit_posts(subreddit, limit=25)
        
        if not posts:
            return {'score': 0, 'signal': 0, 'label': 'neutral', 'posts': 0}
        
        # Extract titles and weights (by score/upvotes)
        titles = [p['title'] for p in posts]
        weights = [max(1, p['score'] / 100) for p in posts]  # Normalize weights
        
        # Analyze with NLP
        result = self.nlp.get_aggregate_sentiment(titles, weights)
        
        # Convert score to signal (-1 to +1 → -1 to +1 signal)
        signal = result['score']
        
        return {
            'score': result['score'],
            'signal': round(signal, 2),
            'label': result['label'],
            'posts': result['count'],
            'bullish': result['bullish_count'],
            'bearish': result['bearish_count'],
            'neutral': result['neutral_count'],
            'model': result['model'],
            'source': f'r/{subreddit}'
        }
    
    def analyze_news(self) -> Dict:
        """Analyze news sentiment using NLP."""
        print("   📡 Fetching news...")
        news = get_crypto_news()
        
        if not news:
            return {'score': 0, 'signal': 0, 'label': 'neutral', 'articles': 0}
        
        titles = [n['title'] for n in news]
        result = self.nlp.get_aggregate_sentiment(titles)
        
        return {
            'score': result['score'],
            'signal': round(result['score'], 2),
            'label': result['label'],
            'articles': result['count'],
            'bullish': result['bullish_count'],
            'bearish': result['bearish_count'],
            'model': result['model'],
            'source': 'News'
        }
    
    def get_combined_sentiment(self) -> Dict:
        """Get complete sentiment analysis from all sources."""
        print("\n🔍 Running NLP Sentiment Analysis...")
        
        # Get all data
        fear_greed = get_fear_greed_index()
        print(f"   ✅ Fear & Greed: {fear_greed['value']} ({fear_greed['classification']})")
        
        reddit_btc = self.analyze_reddit("bitcoin")
        print(f"   ✅ r/bitcoin: {reddit_btc['label']} (score: {reddit_btc['score']:+.3f})")
        
        reddit_crypto = self.analyze_reddit("cryptocurrency")
        print(f"   ✅ r/cryptocurrency: {reddit_crypto['label']} (score: {reddit_crypto['score']:+.3f})")
        
        news = self.analyze_news()
        print(f"   ✅ News: {news['label']} (score: {news['score']:+.3f})")
        
        # Combine with weights
        # Fear & Greed: normalize from 0-100 to -1 to +1
        fg_normalized = (fear_greed['value'] - 50) / 50 * -1  # Invert: high greed = negative
        
        combined_signal = (
            fg_normalized * 1.5 +      # Fear & Greed (1.5x weight)
            reddit_btc['score'] * 1.0 + # Reddit Bitcoin (1.0x)
            reddit_crypto['score'] * 0.5 + # Reddit Crypto (0.5x)
            news['score'] * 1.0          # News (1.0x)
        )
        
        # Normalize to -3 to +3
        max_possible = 1.5 + 1.0 + 0.5 + 1.0
        normalized = (combined_signal / max_possible) * 3
        
        # Determine overall
        if normalized >= 1.5:
            overall = "VERY BULLISH"
            emoji = "🚀"
        elif normalized >= 0.5:
            overall = "BULLISH"
            emoji = "📈"
        elif normalized <= -1.5:
            overall = "VERY BEARISH"
            emoji = "💀"
        elif normalized <= -0.5:
            overall = "BEARISH"
            emoji = "📉"
        else:
            overall = "NEUTRAL"
            emoji = "😐"
        
        return {
            'combined_signal': round(normalized, 2),
            'overall': overall,
            'emoji': emoji,
            'fear_greed': fear_greed,
            'reddit_bitcoin': reddit_btc,
            'reddit_crypto': reddit_crypto,
            'news': news,
            'timestamp': datetime.now().isoformat(),
            'nlp_model': 'FinBERT' if self.nlp.model_loaded else 'Fallback'
        }
    
    def display_analysis(self, sentiment: Dict):
        """Pretty print the sentiment analysis."""
        print("\n" + "=" * 65)
        print("📊 NLP SENTIMENT ANALYSIS RESULTS")
        print("=" * 65)
        
        # Model info
        print(f"\n🧠 Model: {sentiment.get('nlp_model', 'Unknown')}")
        
        # Fear & Greed
        fg = sentiment['fear_greed']
        print(f"\n{fg['emoji']} Fear & Greed Index: {fg['value']} ({fg['classification']})")
        print(f"   Interpretation: {'Buy signal (others fearful)' if fg['value'] < 40 else 'Sell signal (others greedy)' if fg['value'] > 60 else 'Neutral'}")
        
        # Reddit Bitcoin
        rb = sentiment['reddit_bitcoin']
        print(f"\n🔥 Reddit r/bitcoin ({rb['posts']} posts analyzed)")
        print(f"   NLP Score: {rb['score']:+.3f}")
        print(f"   Sentiment: {rb['label'].upper()}")
        print(f"   Breakdown: 📈 {rb.get('bullish', 0)} bullish | 📉 {rb.get('bearish', 0)} bearish | 😐 {rb.get('neutral', 0)} neutral")
        
        # Reddit Crypto
        rc = sentiment['reddit_crypto']
        print(f"\n💬 Reddit r/cryptocurrency ({rc['posts']} posts analyzed)")
        print(f"   NLP Score: {rc['score']:+.3f}")
        print(f"   Sentiment: {rc['label'].upper()}")
        print(f"   Breakdown: 📈 {rc.get('bullish', 0)} bullish | 📉 {rc.get('bearish', 0)} bearish | 😐 {rc.get('neutral', 0)} neutral")
        
        # News
        news = sentiment['news']
        print(f"\n📰 News Headlines ({news['articles']} articles analyzed)")
        print(f"   NLP Score: {news['score']:+.3f}")
        print(f"   Sentiment: {news['label'].upper()}")
        
        # Combined
        print("\n" + "-" * 65)
        print(f"{sentiment['emoji']} OVERALL SENTIMENT: {sentiment['overall']}")
        print(f"   Combined Signal: {sentiment['combined_signal']:+.2f} (scale: -3 to +3)")
        
        # Trading interpretation
        sig = sentiment['combined_signal']
        if sig >= 1.0:
            print(f"\n   💡 Interpretation: Strong bullish sentiment. Consider buying.")
        elif sig >= 0.3:
            print(f"\n   💡 Interpretation: Mildly bullish. Market slightly optimistic.")
        elif sig <= -1.0:
            print(f"\n   💡 Interpretation: Strong bearish sentiment. Consider caution.")
        elif sig <= -0.3:
            print(f"\n   💡 Interpretation: Mildly bearish. Market slightly pessimistic.")
        else:
            print(f"\n   💡 Interpretation: Neutral sentiment. No strong directional bias.")
        
        print("=" * 65)


# For backwards compatibility with existing bot
def get_combined_sentiment() -> Dict:
    """
    Drop-in replacement for the old sentiment function.
    Creates analyzer and returns sentiment.
    """
    try:
        analyzer = AdvancedSentimentAnalyzer()
        return analyzer.get_combined_sentiment()
    except Exception as e:
        print(f"⚠️ Sentiment analysis error: {e}")
        return {
            'combined_signal': 0,
            'overall': 'NEUTRAL',
            'emoji': '😐',
            'fear_greed': {'value': 50, 'classification': 'Neutral', 'signal': 0, 'emoji': '😐'},
            'reddit_bitcoin': {'score': 0, 'signal': 0, 'label': 'neutral', 'posts': 0},
            'reddit_crypto': {'score': 0, 'signal': 0, 'label': 'neutral', 'posts': 0},
            'news': {'score': 0, 'signal': 0, 'label': 'neutral', 'articles': 0}
        }


def display_sentiment(sentiment: Dict):
    """Display function for backwards compatibility."""
    analyzer = AdvancedSentimentAnalyzer()
    analyzer.display_analysis(sentiment)


# ============== MAIN ==============

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("🧠 TESTING NLP SENTIMENT ANALYZER")
    print("=" * 65)
    
    # Test individual text analysis
    analyzer = AdvancedSentimentAnalyzer()
    
    print("\n📝 Testing individual text analysis:")
    test_texts = [
        "Bitcoin is going to the moon! 🚀 Best investment ever!",
        "This is a massive crash, I'm selling everything before it's too late",
        "BTC price is stable around 95k, nothing special happening",
        "I'm not saying it's bullish, but the fundamentals look terrible",  # Sarcasm/negation test
        "The market is definitely NOT crashing, stop spreading FUD"  # Negation test
    ]
    
    for text in test_texts:
        result = analyzer.nlp.analyze_text(text)
        print(f"\n   Text: \"{text[:60]}...\"")
        print(f"   Result: {result['label'].upper()} (score: {result['score']:+.3f})")
    
    # Full analysis
    print("\n" + "=" * 65)
    print("Running full market sentiment analysis...")
    
    sentiment = analyzer.get_combined_sentiment()
    analyzer.display_analysis(sentiment)
