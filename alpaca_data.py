import logging
import asyncio
import pandas as pd
from alpaca_trade_api.rest import REST
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.common import URL
from typing import List, Dict, Optional, Callable, Any
from enum import Enum
import sys
# app.py
# ...
from alpaca_connector import AlpacaConnector as AlpacaData
# ...
# Configure logging (assuming it's configured in the main app or here if standalone)
# For this file, let's ensure it has its own logger if used independently.
logger = logging.getLogger(__name__)
if not logger.hasHandlers(): # Avoid duplicate handlers if already configured
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

class DataFeed(Enum):
    IEX = "iex"
    SIP = "sip"

class AlpacaConnector:
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        paper: bool = False,
        feed: str = "iex", # Default to IEX
        base_url_override: Optional[str] = None # Renamed from base_url to avoid confusion
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper_trading = paper
        self._feed_str = feed.lower()
        
        self.base_url = URL(base_url_override if base_url_override else (
            "https://paper-api.alpaca.markets" if self.paper_trading else "https://api.alpaca.markets"
        ))
        
        self._rest_client: Optional[REST] = None
        self._stream: Optional[Stream] = None
        self._websocket_running: bool = False
        self._websocket_task: Optional[asyncio.Task] = None
        self._latest_trades_cache: Dict[str, Dict[str, Any]] = {} # Cache for latest trade data
        self.is_operational: bool = False # Changed from has_valid_alpaca_keys_and_feed

        logger.info(f"Initializing AlpacaConnector -> Paper: {self.paper_trading}, Feed: {self._feed_str}, Base URL: {self.base_url}")

        # Validate and set data feed
        try:
            self.feed = DataFeed(self._feed_str)
            logger.info(f"Data feed set to: {self.feed.value.upper()}")
        except ValueError:
            logger.error(f"Invalid data feed: '{self._feed_str}'. Must be 'iex' or 'sip'. Connector not operational.")
            self.feed = None # Explicitly set to None
            return # Stop initialization

        # Validate API keys
        if not api_key or not secret_key or api_key == "placeholder_api_key" or secret_key == "placeholder_secret_key":
            logger.error("Invalid or placeholder API keys provided. Connector not operational.")
            return # Stop initialization

        # Initialize REST client
        self._initialize_rest_client()

    def _initialize_rest_client(self):
        try:
            self._rest_client = REST(
                key_id=self.api_key,
                secret_key=self.secret_key,
                base_url=self.base_url
            )
            account = self._rest_client.get_account()
            logger.info(f"✅ REST API authentication successful. Account ID: {account.id}, Status: {account.status}")
            self.is_operational = True
        except Exception as e:
            logger.error(f"❌ Failed to initialize REST client or authenticate: {e}")
            if "authorized" in str(e).lower() or "unauthorized" in str(e).lower():
                logger.error("   Possible issue: Invalid or unauthorized API keys.")
            elif "forbidden" in str(e).lower() or "subscription" in str(e).lower():
                logger.error(f"   Possible issue: Account may not have access to the '{self.feed.value if self.feed else self._feed_str}' feed or other permissions issue.")
            self._rest_client = None
            self.is_operational = False
            
    def test_rest_data_fetch(self, symbol="AAPL") -> bool:
        """Test REST API data fetch for a sample symbol."""
        if not self.is_operational or not self._rest_client:
            logger.error("REST client not operational. Cannot test data fetch.")
            return False
        
        logger.info(f"Attempting to fetch sample data (1Min bars for {symbol}, Feed: {self.feed.value})...")
        try:
            bars_df = self._rest_client.get_bars(
                symbol=symbol,
                timeframe="1Min",
                limit=1,
                feed=self.feed.value # Use the enum's value
            ).df
            
            if not bars_df.empty:
                logger.info(f"✅ REST Data fetch successful. Received {len(bars_df)} bar(s) for {symbol}")
                return True
            else:
                logger.warning(f"REST Data fetch returned no bars for {symbol}. This might be normal if market is closed or symbol is inactive.")
                return False # Still counts as a successful API call if no error
        except Exception as e:
            logger.error(f"❌ REST API data fetch test failed for {symbol}: {e}")
            if "forbidden" in str(e).lower() or "subscription" in str(e).lower():
                logger.error(f"   Possible issue: Account may not have access to '{self.feed.value}' feed for {symbol}.")
            return False

    def get_historical_data(
        self,
        tickers: List[str],
        timeframe_str: str = "1Min",
        limit_per_symbol: int = 300 # Increased default
    ) -> Dict[str, pd.DataFrame]:
        """Fetch historical bar data for given tickers."""
        result = {}
        if not self.is_operational or not self._rest_client:
            logger.error("Cannot fetch historical data: Alpaca client not operational.")
            return result
        if not self.feed: # Check if feed was successfully initialized
            logger.error("Cannot fetch historical data: Data feed not properly configured.")
            return result
        if not tickers:
            logger.warning("No tickers provided for historical data fetch.")
            return result

        logger.info(f"Fetching historical data for {len(tickers)} tickers: {tickers}, Timeframe: {timeframe_str}, Limit: {limit_per_symbol}, Feed: {self.feed.value}")
        for ticker in tickers:
            try:
                bars_df = self._rest_client.get_bars(
                    symbol=ticker,
                    timeframe=timeframe_str,
                    limit=limit_per_symbol,
                    feed=self.feed.value
                ).df
                if not bars_df.empty:
                    # Ensure UTC timezone and lowercase columns
                    if bars_df.index.tz is None:
                        bars_df.index = pd.to_datetime(bars_df.index).tz_localize('UTC')
                    else:
                        bars_df.index = pd.to_datetime(bars_df.index).tz_convert('UTC')
                    bars_df.columns = bars_df.columns.str.lower()
                    
                    required_cols = ['open', 'high', 'low', 'close', 'volume']
                    if not all(col in bars_df.columns for col in required_cols):
                         logger.warning(f"DataFrame for {ticker} is missing some required OHLCV columns. Found: {bars_df.columns.tolist()}")
                    
                    result[ticker] = bars_df
                    logger.debug(f"Successfully fetched {len(bars_df)} bars for {ticker}.")
                else:
                    logger.warning(f"No historical bars returned for {ticker}.")
            except Exception as e:
                logger.error(f"Error fetching historical data for {ticker}: {e}")
                if "forbidden" in str(e).lower() or "subscription" in str(e).lower():
                    logger.error(f"   Possible issue: Account may not have access to '{self.feed.value}' feed for {ticker}.")
        return result

    def get_latest_trade(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch the latest trade for a ticker."""
        if not self.is_operational or not self._rest_client:
            logger.warning(f"Cannot fetch latest trade for {ticker}: Alpaca client not operational.")
            return self._latest_trades_cache.get(ticker)
        if not self.feed:
            logger.warning(f"Cannot fetch latest trade for {ticker}: Data feed not configured.")
            return self._latest_trades_cache.get(ticker)

        try:
            trade = self._rest_client.get_latest_trade(symbol=ticker, feed=self.feed.value)
            trade_data = {
                "price": trade.price,
                "size": trade.size,
                "timestamp": pd.to_datetime(trade.timestamp, utc=True) # Alpaca SDK returns datetime object
            }
            self._latest_trades_cache[ticker] = trade_data
            logger.debug(f"Fetched latest trade for {ticker}: Price={trade.price}, Time={trade.timestamp}")
            return trade_data
        except Exception as e:
            logger.error(f"Error fetching latest trade for {ticker}: {e}")
            return self._latest_trades_cache.get(ticker) # Return cached if available on error

    async def _default_bar_handler(self, bar):
        logger.debug(f"WS Bar {bar.symbol}: C={bar.close} V={bar.volume} @ {bar.timestamp}")

    async def _default_trade_handler(self, trade):
        logger.debug(f"WS Trade {trade.symbol}: P={trade.price} S={trade.size} @ {trade.timestamp}")
        # Update cache
        self._latest_trades_cache[trade.symbol] = {
            "price": trade.price, "size": trade.size, 
            "timestamp": pd.to_datetime(trade.timestamp, utc=True)
        }

    async def start_stream(
        self, 
        symbols: List[str], 
        on_bar: Optional[Callable] = None, 
        on_trade: Optional[Callable] = None
    ) -> None:
        """Start WebSocket stream for given symbols."""
        if not self.is_operational:
            logger.error("Cannot start WebSocket: Alpaca client not operational.")
            return
        if not self.feed:
            logger.error("Cannot start WebSocket: Data feed not configured.")
            return
        if self._websocket_running:
            logger.warning("WebSocket stream is already running.")
            return
        if not symbols:
            logger.warning("No symbols provided for WebSocket streaming.")
            return

        logger.info(f"Starting WebSocket stream for {len(symbols)} symbols: {symbols} (Feed: {self.feed.value})")

        bar_handler_to_use = on_bar if on_bar else self._default_bar_handler
        trade_handler_to_use = on_trade if on_trade else self._default_trade_handler
        
        try:
            self._stream = Stream(
                key_id=self.api_key,
                secret_key=self.secret_key,
                base_url=self.base_url, # Uses the same base_url as REST for paper/live determination
                data_feed=self.feed.value,
                raw_data=False # Processed data is usually easier
            )

            for symbol in symbols:
                self._stream.subscribe_bars(bar_handler_to_use, symbol)
                self._stream.subscribe_trades(trade_handler_to_use, symbol)

            self._websocket_running = True
            # The Stream object's _run_forever() is the main loop for the websocket
            self._websocket_task = asyncio.create_task(self._stream._run_forever()) 
            logger.info("✅ WebSocket stream started.")
            
            await self._websocket_task # This will run until the task is cancelled or an error occurs

        except asyncio.CancelledError:
            logger.info("WebSocket stream task was cancelled.")
        except Exception as e:
            logger.error(f"❌ WebSocket stream failed: {e}")
            if "forbidden" in str(e).lower() or "subscription" in str(e).lower():
                logger.error(f"   Possible issue: Account may not have access to '{self.feed.value}' feed for streaming.")
            self._websocket_running = False # Ensure flag is reset on error
        finally:
            # Ensure cleanup if start_stream exits unexpectedly
            if self._websocket_running: # if it was set to true but an error occurred before explicit stop
                 await self.stop_stream(from_finally=True)


    async def stop_stream(self, from_finally=False) -> None:
        """Stop the WebSocket stream cleanly."""
        if not self._websocket_running or not self._stream:
            if not from_finally: # Avoid verbose logging if called from finally block of start_stream
                logger.debug("WebSocket already stopped or not initialized.")
            return

        logger.info("Stopping WebSocket stream...")
        try:
            await self._stream.stop_ws() # Alpaca SDK method to close WebSocket
            if self._websocket_task and not self._websocket_task.done():
                self._websocket_task.cancel()
                try:
                    await self._websocket_task # Allow cancellation to propagate
                except asyncio.CancelledError:
                    logger.info("WebSocket task successfully cancelled by stop_stream.")
            logger.info("✅ WebSocket stream stopped successfully.")
        except Exception as e:
            logger.error(f"Error stopping WebSocket stream: {e}")
        finally: # Ensure state is reset
            self._websocket_running = False
            self._stream = None
            self._websocket_task = None
            
    async def test_websocket_connection(self, symbols=["AAPL"], duration_sec=10):
        """Test WebSocket connection for a short duration."""
        if not self.is_operational:
            logger.error("Cannot test WebSocket: Client not operational.")
            return False
        
        logger.info(f"Testing WebSocket connection (Feed: {self.feed.value}, Symbols: {symbols}, Duration: {duration_sec}s)")
        
        received_bar_count = 0
        received_trade_count = 0

        async def test_bar_handler(bar):
            nonlocal received_bar_count
            received_bar_count +=1
            logger.info(f"[Test WS] Bar: {bar.symbol} C={bar.close} @ {bar.timestamp} (Total Bars: {received_bar_count})")
        
        async def test_trade_handler(trade):
            nonlocal received_trade_count
            received_trade_count +=1
            logger.info(f"[Test WS] Trade: {trade.symbol} P={trade.price} (Total Trades: {received_trade_count})")

        stream_run_task = asyncio.create_task(
            self.start_stream(symbols, on_bar=test_bar_handler, on_trade=test_trade_handler)
        )
        
        await asyncio.sleep(duration_sec)
        
        logger.info(f"Test duration elapsed. Stopping WebSocket test stream... (Received: {received_bar_count} bars, {received_trade_count} trades)")
        await self.stop_stream()
        
        try:
            await stream_run_task 
        except asyncio.CancelledError:
             logger.info("WebSocket test run task properly cancelled.")

        if not self._websocket_running and (received_bar_count > 0 or received_trade_count > 0):
            logger.info(f"✅ WebSocket test completed. Received {received_bar_count} bars and {received_trade_count} trades.")
            return True
        elif not self._websocket_running: # Stream stopped but no data
            logger.warning(f"✅ WebSocket test completed, but received NO data. Check symbol activity or feed subscription for {symbols}.")
            return True 
        else: # Stream didn't stop cleanly or other issue
            logger.error("❌ WebSocket test may not have stopped cleanly or failed to receive data.")
            return False

    async def close(self):
        """Cleanly close all connections and resources."""
        logger.info("Closing AlpacaConnector...")
        if self._websocket_running:
            await self.stop_stream()
        # Potentially other cleanup for REST client if needed, though usually not necessary
        logger.info("AlpacaConnector closed.")

    async def __aenter__(self):
        if not self.is_operational:
            # Attempt re-initialization if needed, or raise
            self._initialize_rest_client() # Ensure it's tried on entry
            if not self.is_operational:
                raise ConnectionError("AlpacaConnector failed to initialize and is not operational.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()