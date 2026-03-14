import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any

class BacktestingService:
    """Service to validate current AI analysis against historical price action."""
    
    @staticmethod
    def run_simple_backtest(df: pd.DataFrame, days: int = 30) -> Dict[str, Any]:
        """
        Calculates what the performance would be if the stock was bought 'days' ago
        and compared to the current price.
        """
        if df.empty or len(df) < 5:
            return {"status": "error", "message": "Insufficient data"}
        
        # Ensure timestamp is datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        current_price = float(df.iloc[-1]['close'])
        
        # Find price N days ago (approximate)
        target_date = df.iloc[-1]['timestamp'] - timedelta(days=days)
        past_df = df[df['timestamp'] <= target_date]
        
        if past_df.empty:
            # Fallback to the oldest available if not enough history for 'days'
            entry_row = df.iloc[0]
        else:
            entry_row = past_df.iloc[-1]
            
        entry_price = float(entry_row['close'])
        entry_date = entry_row['timestamp'].strftime('%Y-%m-%d')
        
        price_change = current_price - entry_price
        returns_pct = (price_change / entry_price) * 100
        
        max_price = float(df[df['timestamp'] >= entry_row['timestamp']]['high'].max())
        min_price = float(df[df['timestamp'] >= entry_row['timestamp']]['low'].min())
        
        max_return = ((max_price - entry_price) / entry_price) * 100
        max_drawdown = ((min_price - entry_price) / entry_price) * 100

        return {
            "status": "success",
            "entry_date": entry_date,
            "entry_price": entry_price,
            "current_price": current_price,
            "returns_pct": round(returns_pct, 2),
            "max_return": round(max_return, 2),
            "max_drawdown": round(max_drawdown, 2),
            "period_days": days
        }
