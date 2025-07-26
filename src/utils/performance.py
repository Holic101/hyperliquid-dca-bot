"""Performance optimization utilities."""

import streamlit as st
import time
import functools
from typing import Any, Callable, Optional
from datetime import datetime, timedelta

from .logging_config import get_logger

logger = get_logger(__name__)


class StreamlitCache:
    """Enhanced caching for Streamlit applications."""
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator for caching function results."""
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Check if we have cached data
            if hasattr(st.session_state, 'cache_data'):
                cache_data = st.session_state.cache_data
                if cache_key in cache_data:
                    cached_time, cached_result = cache_data[cache_key]
                    if time.time() - cached_time < self.ttl_seconds:
                        logger.debug(f"Using cached result for {func.__name__}")
                        return cached_result
            else:
                st.session_state.cache_data = {}
            
            # Execute function and cache result
            logger.debug(f"Executing {func.__name__} and caching result")
            result = func(*args, **kwargs)
            st.session_state.cache_data[cache_key] = (time.time(), result)
            
            return result
        
        return wrapper


def clear_streamlit_cache():
    """Clear all cached data in Streamlit session state."""
    if hasattr(st.session_state, 'cache_data'):
        st.session_state.cache_data.clear()
        logger.info("Streamlit cache cleared")


def performance_monitor(func: Callable) -> Callable:
    """Decorator to monitor function performance."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > 1.0:  # Log slow operations
                logger.warning(f"{func.__name__} took {execution_time:.2f}s to execute")
            else:
                logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper


async def async_performance_monitor(func: Callable) -> Callable:
    """Decorator to monitor async function performance."""
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > 1.0:  # Log slow operations
                logger.warning(f"{func.__name__} took {execution_time:.2f}s to execute")
            else:
                logger.debug(f"{func.__name__} executed in {execution_time:.3f}s")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.3f}s: {e}")
            raise
    
    return wrapper


class DataLoader:
    """Optimized data loading with batch operations."""
    
    def __init__(self, api_client):
        self.api_client = api_client
        self._batch_cache = {}
        self._cache_timeout = timedelta(seconds=30)
    
    async def load_dashboard_data(self, config, force_refresh: bool = False):
        """Load all dashboard data in optimized batches."""
        cache_key = f"dashboard_data_{config.wallet_address}"
        
        # Check cache
        if not force_refresh and cache_key in self._batch_cache:
            cached_time, cached_data = self._batch_cache[cache_key]
            if datetime.now() - cached_time < self._cache_timeout:
                logger.debug("Using cached dashboard data")
                return cached_data
        
        logger.info("Loading dashboard data...")
        start_time = time.time()
        
        try:
            # Load data concurrently where possible
            import asyncio
            
            tasks = [
                self.api_client.get_current_price(),
                self.api_client.get_account_balance(config.wallet_address, "USDC"),
                self.api_client.get_account_balance(config.wallet_address, "UBTC"),
                self.api_client.get_historical_prices(config.volatility_window)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            current_price = results[0] if not isinstance(results[0], Exception) else None
            usdc_balance = results[1] if not isinstance(results[1], Exception) else 0.0
            ubtc_balance = results[2] if not isinstance(results[2], Exception) else 0.0
            historical_prices = results[3] if not isinstance(results[3], Exception) else None
            
            dashboard_data = {
                'current_price': current_price,
                'usdc_balance': usdc_balance,
                'ubtc_balance': ubtc_balance,
                'historical_prices': historical_prices,
                'last_updated': datetime.now()
            }
            
            # Cache the data
            self._batch_cache[cache_key] = (datetime.now(), dashboard_data)
            
            execution_time = time.time() - start_time
            logger.info(f"Dashboard data loaded in {execution_time:.2f}s")
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error loading dashboard data: {e}")
            return None
    
    def clear_cache(self):
        """Clear the data loader cache."""
        self._batch_cache.clear()
        logger.info("Data loader cache cleared")


def optimize_dataframe_display(df, max_rows: int = 100):
    """Optimize DataFrame for display in Streamlit."""
    if df is None or df.empty:
        return df
    
    # Limit rows for performance
    if len(df) > max_rows:
        logger.info(f"Limiting DataFrame display to {max_rows} rows (was {len(df)})")
        return df.tail(max_rows)
    
    return df


def batch_ui_updates(func: Callable) -> Callable:
    """Decorator to batch UI updates for better performance."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Use empty containers to batch updates
        with st.container():
            return func(*args, **kwargs)
    
    return wrapper