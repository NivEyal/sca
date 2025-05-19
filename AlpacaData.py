import logging
import asyncio
import sys
import pandas as pd
from alpaca_trade_api.rest import REST
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.common import URL 
from typing import List, Dict, Optional, Callable, Any
from enum import Enum

class DataFeed(str, Enum):
    SIP = "sip"
    IEX = "iex"

logger = logging.getLogger(__name__)

class AlpacaConnector:
    def __init__(self, api_key: str, secret_key: str, paper_trading: bool = False, data_feed: str = "iex"):
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper_trading = paper_trading
        self.data_feed = data_feed.lower() 
        self.base_url = URL("https://paper-api.alpaca.markets" if self.paper_trading else "https://api.alpaca.markets")

        self._rest_client: Optional[REST] = None
        self._stream: Optional[Stream] = None
        self._websocket_running: bool = False
        self._websocket_task: Optional[asyncio.Task] = None
        self.is_operational: bool = False 

        self._stream_data_cache = { # Cache for latest stream data if needed by handlers
            "bars": {}, 
            "trades": {} 
        }
        self._initialize_rest_client()
class AlpacaData:
    def __init__(self, api_key, secret_key, paper, feed, base_url):
        # Initialize your connection here
        pass

    def _initialize_rest_client(self):
        logger.info(f"Initializing Alpaca REST client. Paper: {self.paper_trading}, Feed: {self.data_feed}, URL: {self.base_url}")
        if not self.api_key or self.api_key == "AK8ASFLORVBDJ80AK1BM" or \
           not self.secret_key or self.secret_key == "iYaL9eqKjL97C2MgJfJDD1IErfzzJJwTvfFPgb0b":
            logger.error("Invalid or placeholder API keys provided. REST client not initialized.")
            return

        if self.data_feed not in ["iex", "sip"]:
            logger.error(f"Invalid data feed: {self.data_feed}. Must be 'iex' or 'sip'. REST client not initialized.")
            return

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
            if "authorized" in str(e).lower() or "forbidden" in str(e).lower():
                logger.error("   Possible issue: Invalid API keys or insufficient permissions/subscription for chosen feed.")
            self._rest_client = None
            self.is_operational = False

    def test_rest_data_fetch(self, symbol="AAPL") -> bool:
        """Test REST API data fetch for a sample symbol."""
        if not self.is_operational or not self._rest_client:
            logger.error("REST client not operational. Cannot test data fetch.")
            return False
        
        logger.info(f"Attempting to fetch sample data (1Min bars for {symbol}, Feed: {self.data_feed})...")
        try:
            bars_df = self._rest_client.get_bars(
                symbol=symbol,
                timeframe="1Min",
                limit=1,
                feed=self.data_feed
            ).df
            
            if not bars_df.empty:
                logger.info(f"✅ REST Data fetch successful. Received {len(bars_df)} bar(s) for {symbol}")
                logger.debug(f"Sample bar: {bars_df.iloc[0].to_dict()}")
                return True
            else:
                logger.warning(f"REST Data fetch returned no bars for {symbol}")
                return False
        except Exception as e:
            logger.error(f"❌ REST API data fetch test failed for {symbol}: {e}")
            if "forbidden" in str(e).lower() or "subscription" in str(e).lower():
                logger.error(f"   Possible issue: Account may not have access to '{self.data_feed}' feed for {symbol}.")
            return False

    def get_historical_data(
        self,
        tickers: List[str],
        timeframe_str: str = "1Min", 
        limit_per_symbol: int = 300 
    ) -> Dict[str, pd.DataFrame]:
        """Fetch historical bar data."""
        all_data = {}
        if not self.is_operational or not self._rest_client:
            logger.error("REST client not operational. Cannot fetch historical data.")
            return all_data

        if not tickers:
            logger.warning("No tickers provided for historical data.")
            return all_data

        logger.info(f"Fetching historical data for {tickers} (Timeframe: {timeframe_str}, Limit: {limit_per_symbol}, Feed: {self.data_feed})")
        for ticker in tickers:
            try:
                bars_df = self._rest_client.get_bars(
                    symbol=ticker,
                    timeframe=timeframe_str,
                    limit=limit_per_symbol,
                    feed=self.data_feed
                ).df

                if not bars_df.empty:
                    if bars_df.index.tz is None:
                        bars_df.index = pd.to_datetime(bars_df.index).tz_localize('UTC')
                    else:
                        bars_df.index = pd.to_datetime(bars_df.index).tz_convert('UTC')
                    
                    bars_df.columns = bars_df.columns.str.lower()
                    required_cols = ['open', 'high', 'low', 'close', 'volume']
                    if not all(col in bars_df.columns for col in required_cols):
                        logger.warning(f"DataFrame for {ticker} is missing some required OHLCV columns after lowercasing. Found: {bars_df.columns.tolist()}")
                    
                    all_data[ticker] = bars_df
                    logger.info(f"Fetched {len(bars_df)} bars for {ticker}.")
                else:
                    logger.warning(f"No historical data returned for {ticker}.")
            except Exception as e:
                logger.error(f"Error fetching historical data for {ticker}: {e}")
                if "forbidden" in str(e).lower() or "subscription" in str(e).lower():
                    logger.error(f"   Possible issue: Account may not have access to '{self.data_feed}' feed for {ticker}.")
        return all_data

    async def _default_bar_handler(self, bar):
        logger.debug(f"WS Bar {bar.symbol}: C={bar.close} V={bar.volume} @ {bar.timestamp}")
        # Example: Update internal cache
        self._stream_data_cache["bars"].setdefault(bar.symbol, []).append(bar)
        # Keep cache size manageable if storing many bars
        self._stream_data_cache["bars"][bar.symbol] = self._stream_data_cache["bars"][bar.symbol][-100:]


    async def _default_trade_handler(self, trade):
        logger.debug(f"WS Trade {trade.symbol}: P={trade.price} S={trade.size} @ {trade.timestamp}")
        self._stream_data_cache["trades"].setdefault(trade.symbol, []).append(trade)
        self._stream_data_cache["trades"][trade.symbol] = self._stream_data_cache["trades"][trade.symbol][-100:]


    async def start_stream(
        self,
        symbols: List[str],
        on_bar: Optional[Callable] = None,
        on_trade: Optional[Callable] = None
    ):
        """Start WebSocket data stream for given symbols."""
        if not self.is_operational: 
            logger.error("Cannot start WebSocket stream: Client not operational (check REST init).")
            return
        if self._websocket_running:
            logger.warning("WebSocket stream is already running.")
            return
        if not symbols:
            logger.warning("No symbols provided for WebSocket stream.")
            return

        logger.info(f"Starting WebSocket stream for {symbols} (Feed: {self.data_feed})")
        
        bar_handler_to_use = on_bar if on_bar else self._default_bar_handler
        trade_handler_to_use = on_trade if on_trade else self._default_trade_handler

        try:
            self._stream = Stream(
                key_id=self.api_key,
                secret_key=self.secret_key,
                base_url=self.base_url, 
                data_feed=self.data_feed,
                raw_data=False 
            )

            for symbol in symbols:
                self._stream.subscribe_bars(bar_handler_to_use, symbol)
                self._stream.subscribe_trades(trade_handler_to_use, symbol)
            
            self._websocket_running = True
            self._websocket_task = asyncio.create_task(self._stream._run_forever()) 
            logger.info("✅ WebSocket stream started.")
            
            await self._websocket_task 

        except asyncio.CancelledError:
            logger.info("WebSocket stream task was cancelled.")
        except Exception as e:
            logger.error(f"❌ WebSocket stream failed: {e}")
            if "forbidden" in str(e).lower() or "subscription" in str(e).lower():
                logger.error(f"   Possible issue: Account may not have access to '{self.data_feed}' feed.")
            self._websocket_running = False 
        finally:
            if self._websocket_running: 
                await self.stop_stream(from_finally=True)


    async def stop_stream(self, from_finally=False):
        """Stop the WebSocket data stream."""
        if not self._websocket_running or not self._stream:
            if not from_finally: 
                 logger.debug("WebSocket stream is not running or not initialized.")
            return

        logger.info("Stopping WebSocket stream...")
        try:
            await self._stream.stop_ws() 
            
            if self._websocket_task and not self._websocket_task.done():
                self._websocket_task.cancel()
                try:
                    await self._websocket_task 
                except asyncio.CancelledError:
                    logger.info("WebSocket task successfully cancelled by stop_stream.")
            
            logger.info("✅ WebSocket stream stopped.")
        except Exception as e:
            logger.error(f"Error stopping WebSocket stream: {e}")
        finally:
            self._websocket_running = False
            self._websocket_task = None
            self._stream = None 

    async def test_websocket_connection(self, symbols=["AAPL"], duration_sec=10):
        """Test WebSocket connection for a short duration."""
        if not self.is_operational:
            logger.error("Cannot test WebSocket: Client not operational.")
            return False
        
        logger.info(f"Testing WebSocket connection (Feed: {self.data_feed}, Symbols: {symbols}, Duration: {duration_sec}s)")
        
        received_bar_count = 0
        received_trade_count = 0

        async def test_bar_handler(bar):
            nonlocal received_bar_count
            received_bar_count +=1
            logger.info(f"[Test WS] Bar: {bar.symbol} C={bar.close} @ {bar.timestamp} (Total: {received_bar_count})")
        
        async def test_trade_handler(trade):
            nonlocal received_trade_count
            received_trade_count +=1
            logger.info(f"[Test WS] Trade: {trade.symbol} P={trade.price} (Total: {received_trade_count})")

        # Run start_stream in a background task so we can time it out
        stream_run_task = asyncio.create_task(
            self.start_stream(symbols, on_bar=test_bar_handler, on_trade=test_trade_handler)
        )
        
        await asyncio.sleep(duration_sec) # Let the stream run for the specified duration
        
        logger.info(f"Test duration elapsed. Stopping WebSocket test stream... (Bars: {received_bar_count}, Trades: {received_trade_count})")
        await self.stop_stream() # This will cancel the stream_run_task internally
        
        try:
            await stream_run_task # Wait for the start_stream task to finish its cleanup
        except asyncio.CancelledError:
             logger.info("WebSocket test run task properly cancelled.")

        if not self._websocket_running and received_bar_count + received_trade_count > 0:
            logger.info(f"✅ WebSocket test completed successfully. Received {received_bar_count} bars and {received_trade_count} trades.")
            return True
        elif not self._websocket_running:
            logger.warning(f"✅ WebSocket test completed, but received no data (Bars: {received_bar_count}, Trades: {received_trade_count}). Check symbol activity or feed subscription.")
            return True # Test completed, but no data
        else:
            logger.error("❌ WebSocket test may not have stopped cleanly or failed to receive data.")
            return False

    async def close(self):
        """Cleanly close connections."""
        logger.info("Closing AlpacaConnector...")
        if self._websocket_running:
            await self.stop_stream()
        logger.info("AlpacaConnector closed.")

    async def __aenter__(self):
        if not self.is_operational:
            # Attempt re-initialization if needed, or raise
            self._initialize_rest_client()
            if not self.is_operational:
                raise ConnectionError("Alpaca REST client failed to initialize.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()