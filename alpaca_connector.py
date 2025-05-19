import logging
import asyncio
import pandas as pd
from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit, APIError
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.common import URL
from alpaca_trade_api.entity import Bar as AlpacaBar, Trade as AlpacaTrade, Quote as AlpacaQuote
from typing import List, Dict, Optional, Callable, Any, Tuple, Union
from enum import Enum
import finnhub
import yfinance as yf
from datetime import datetime, timedelta, timezone
from tradingview_ta import TA_Handler, Interval, Exchange
from typing import Awaitable
try:
    import streamlit as st
except ImportError:
    st = None
from functools import wraps



logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
def get_tradingview_analysis(symbol: str) -> Optional[Dict[str, Any]]:
    try:
        handler = TA_Handler(
            symbol=symbol,
            screener="america",  # Change if needed: "crypto", "forex", etc.
            exchange="NASDAQ",   # Change based on asset location
            interval=Interval.INTERVAL_1_DAY
        )
        analysis = handler.get_analysis()
        return {
            "summary": analysis.summary,
            "indicators": analysis.indicators
        }
    except Exception as e:
        logger.warning(f"TradingView TA fallback failed for {symbol}: {e}")
        return None

def get_latest_price_and_change(alpaca_client, symbol: str, timeframe_str: str = "5Min") -> Dict:
    try:
        bars = alpaca_client.get_historical_data(symbol, timeframe_str=timeframe_str, limit=2)
        df = bars.get(symbol)
        if df is None or len(df) < 2:
            return {"symbol": symbol, "error": "Not enough data"}

        prev_close = df.iloc[-2]["close"]
        last_close = df.iloc[-1]["close"]
        pct_change = ((last_close - prev_close) / prev_close) * 100

        return {
            "symbol": symbol,
            "last_close": last_close,
            "prev_close": prev_close,
            "pct_change": round(pct_change, 2)
        }

    except Exception as e:
        return {"symbol": symbol, "error": str(e)}
class DataFeed(str, Enum):
    SIP = "sip"
    IEX = "iex"
    OTC = "otc"

class AlpacaConnector:
    def __init__(
        self,
        paper: bool = False,
        feed: DataFeed = DataFeed.IEX,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        finnhub_api_key: Optional[str] = None,
    ):
        _api_key = api_key
        _secret_key = secret_key
        _finnhub_api_key = finnhub_api_key

        if st and (not _api_key or not _secret_key):
            logger.debug("Attempting to load Alpaca API keys from Streamlit secrets.")
            try:
                key_suffix = "PAPER" if paper else "LIVE"
                _api_key = st.secrets.get(f"ALPACA_API_KEY_{key_suffix}", _api_key)
                _secret_key = st.secrets.get(f"ALPACA_SECRET_KEY_{key_suffix}", _secret_key)
                if api_key != _api_key : logger.info(f"Loaded Alpaca API Key from st.secrets for {'paper' if paper else 'live'}.")
            except Exception as e:
                logger.warning(f"Could not load Alpaca keys from Streamlit secrets: {e}")
        
        if st and not _finnhub_api_key:
            logger.debug("Attempting to load Finnhub API key from Streamlit secrets.")
            try:
                _finnhub_api_key = st.secrets.get("FINNHUB_API_KEY", _finnhub_api_key)
                if finnhub_api_key != _finnhub_api_key: logger.info("Loaded Finnhub API key from st.secrets.")
            except Exception as e:
                logger.warning(f"Could not load Finnhub API key from Streamlit secrets: {e}")

        self.api_key: str = _api_key or ""
        self.secret_key: str = _secret_key or ""
        self.finnhub_api_key: Optional[str] = _finnhub_api_key

        self.paper_trading: bool = paper
        self.data_feed_type: DataFeed = feed
        self.data_feed: str = feed  # ✔️ Correct

        self.base_url: str = base_url or (
            "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"
        )

        self._finnhub_client: Optional[finnhub.Client] = None
        if self.finnhub_api_key:
            try:
                self._finnhub_client = finnhub.Client(api_key=self.finnhub_api_key)
                if self._finnhub_client.company_profile2(symbol='AAPL').get('name'): # Test call
                    logger.info("✅ Finnhub client initialized and tested successfully.")
                else:
                    logger.warning("⚠️ Finnhub client initialized, but test call failed. Key might be invalid/limited.")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Finnhub client: {e}")
        else:
            logger.info("Finnhub API key not provided. Finnhub fallback unavailable.")

        self._rest_client: Optional[REST] = None
        self.is_operational: bool = False
        if self.api_key and self.secret_key:
            self._initialize_rest_client()
        else:
            logger.error("❌ Alpaca API Key or Secret Key is missing. Client not initialized.")

        self._stream: Optional[Stream] = None
        self._websocket_task: Optional[asyncio.Task] = None
        self._websocket_running: bool = False
        self._stream_data_cache: Dict[str, Dict[str, List[Any]]] = {"bars": {}, "trades": {}, "quotes": {}}


    def _initialize_rest_client(self):
        logger.info(f"Initializing Alpaca REST (Paper: {self.paper_trading}, Feed: {self.data_feed}, URL: {self.base_url})")
        try:
            self._rest_client = REST(
                key_id=self.api_key, secret_key=self.secret_key,
                base_url=URL(self.base_url)
            )
            account = self._rest_client.get_account()
            logger.info(f"✅ Alpaca REST client authenticated. Account: {account.id}, Status: {account.status}")
            self.is_operational = True
        except APIError as e:
            logger.error(f"❌ Alpaca API Error during REST client initialization: {e} (Status: {e.status_code})")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Alpaca REST client: {e}")

    @staticmethod
    def _parse_timeframe(tf_str: str) -> TimeFrame:
        # Simplified parser, assumes format like "1Min", "15Minute", "1Day"
        s = ''.join(filter(str.isdigit, tf_str))
        unit_str = ''.join(filter(str.isalpha, tf_str))
        amount = int(s) if s else 1 # Default to 1 if no number found (e.g. "Day")

        unit_map = {
            "Min": TimeFrameUnit.Minute, "Minute": TimeFrameUnit.Minute,
            "H": TimeFrameUnit.Hour, "Hour": TimeFrameUnit.Hour,
            "D": TimeFrameUnit.Day, "Day": TimeFrameUnit.Day,
            "W": TimeFrameUnit.Week, "Week": TimeFrameUnit.Week,
            "M": TimeFrameUnit.Month, "Mo": TimeFrameUnit.Month, "Month": TimeFrameUnit.Month
        }
        for k, v in unit_map.items():
            if unit_str.lower().startswith(k.lower()):
                return TimeFrame(amount, v)
        raise ValueError(f"Invalid timeframe string: '{tf_str}'")

    @staticmethod
    def _datetime_to_iso(dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None

    @staticmethod
    def _iso_to_datetime(iso_str: Optional[str]) -> Optional[datetime]:
        if not iso_str: return None
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning(f"Invalid ISO date string: {iso_str}")
            return None

    @staticmethod
    def _normalize_dataframe(df: pd.DataFrame, symbol: str, source: str) -> pd.DataFrame:
        if df.empty: return df
        df.columns = [col.lower() for col in df.columns]
        if 'timestamp' in df.columns: df = df.set_index('timestamp') # Finnhub specific
        if not isinstance(df.index, pd.DatetimeIndex):
             try: df.index = pd.to_datetime(df.index, utc=True)
             except: logger.error(f"Failed to convert index to DatetimeIndex for {symbol} from {source}"); return pd.DataFrame()

        if df.index.tz is None: df.index = df.index.tz_localize('UTC')
        else: df.index = df.index.tz_convert('UTC')
        
        df = df[~df.index.duplicated(keep='first')] # Remove duplicates
        # Ensure essential columns exist, prefer 'adj close' if available from yfinance
        col_map = {'adj close': 'close'} # yfinance specific
        df.rename(columns=col_map, inplace=True)
        
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                df[col] = pd.NA # Add missing required columns as NA
        
        return df[required_cols].sort_index().astype(float)
    

    def get_historical_data(
        self,
        tickers: Union[str, List[str]],
        timeframe_str: str = "1Day",
        start_date_iso: Optional[str] = None,
        end_date_iso: Optional[str] = None,
        limit: Optional[int] = None, # Alpaca uses limit if start is not given
        adjustment: str = 'raw' # Alpaca specific: 'raw', 'split', 'dividend', 'all'
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetches historical bar data.
        Uses Alpaca, then Finnhub, then Yahoo Finance as fallbacks.
        All dataframes are normalized (UTC index, ohlcv columns).
        """
        if isinstance(tickers, str): tickers = [tickers]
        all_data: Dict[str, pd.DataFrame] = {ticker: pd.DataFrame() for ticker in tickers}

        try:
            tf = self._parse_timeframe(timeframe_str)
        except ValueError as e:
            logger.error(f"Historical data fetch failed: {e}")
            return all_data

        start_dt = self._iso_to_datetime(start_date_iso)
        end_dt = self._iso_to_datetime(end_date_iso) or datetime.now(timezone.utc)

        if not start_dt and limit is None and tf.unit != TimeFrameUnit.Day: # For intraday, limit or start usually needed
            limit = 300 # Default limit if nothing else specified for intraday
            logger.info(f"No start_date_iso or limit provided for intraday; using default limit={limit}")
        elif not start_dt and limit is None and tf.unit == TimeFrameUnit.Day:
             start_dt = end_dt - timedelta(days=365 * 2) # Default 2 years for daily if no start/limit
             logger.info(f"No start_date_iso or limit provided for daily; using default start date 2 years ago.")


        for symbol in tickers:
            df = pd.DataFrame()
            source = "N/A"

            # 1. Try Alpaca
            if self.is_operational and self._rest_client:
                try:
                    logger.info(f"Fetching {symbol} from Alpaca ({tf}, start={start_dt}, end={end_dt}, limit={limit if not start_dt else None})")
                    alpaca_bars = self._rest_client.get_bars(
                        symbol=symbol, timeframe=tf,
                        start=self._datetime_to_iso(start_dt),
                        end=self._datetime_to_iso(end_dt),
                        limit=limit if not start_dt else None, # Alpaca uses limit if start is not specified
                        feed=self.data_feed, adjustment=adjustment
                    ).df
                    if not alpaca_bars.empty:
                        df = self._normalize_dataframe(alpaca_bars, symbol, "Alpaca")
                        source = "Alpaca"
                except APIError as e:
                    logger.warning(f"Alpaca APIError for {symbol}: {e} (status: {e.status_code})")
                except Exception as e:
                    logger.warning(f"Error fetching {symbol} from Alpaca: {e}")

            # 2. Try Finnhub if Alpaca failed or returned empty
            if df.empty and self._finnhub_client and start_dt: # Finnhub needs start/end
                fh_res = self._map_timeframe_to_finnhub_resolution(tf)
                if fh_res:
                    try:
                        logger.info(f"Fetching {symbol} from Finnhub (res={fh_res}, start={start_dt}, end={end_dt})")
                        fh_bars = self._get_finnhub_bars_fallback(symbol, fh_res, start_dt, end_dt)
                        if not fh_bars.empty:
                            df = self._normalize_dataframe(fh_bars, symbol, "Finnhub")
                            source = "Finnhub"
                    except Exception as e: # Catching Finnhub-specific errors in the helper
                        logger.warning(f"Error fetching {symbol} from Finnhub: {e}")
                else:
                    logger.debug(f"Timeframe {tf} not mappable for Finnhub for {symbol}.")
            
            # 3. Try Yahoo Finance if previous attempts failed
            if df.empty:
                yf_interval, yf_period = self._map_timeframe_to_yfinance_interval(tf)
                if yf_interval:
                    try:
                        # yFinance logic: use start/end if available, otherwise use suggested period
                        yf_start = start_dt if start_dt else None
                        yf_end = end_dt if yf_start else None # Only use end if start is also used
                        
                        logger.info(f"Fetching {symbol} from yFinance (interval={yf_interval}, start={yf_start}, end={yf_end}, period={yf_period if not yf_start else None})")
                        yf_params = {"interval": yf_interval}
                        if yf_start and yf_end:
                            yf_params["start"] = yf_start.strftime('%Y-%m-%d')
                            yf_params["end"] = (yf_end + timedelta(days=1)).strftime('%Y-%m-%d') # yf end is exclusive
                        elif yf_period:
                             yf_params["period"] = yf_period
                        else: # Fallback if somehow no period or start/end
                            yf_params["period"] = "1y"


                        yf_bars = yf.download(symbol, progress=False, auto_adjust=True, actions=False, **yf_params)
                        if not yf_bars.empty:
                            df = self._normalize_dataframe(yf_bars, symbol, "yFinance")
                            source = "yFinance"
                    except Exception as e:
                        logger.warning(f"Error fetching {symbol} from yFinance: {e}")
            
            if not df.empty:
                logger.warning(f"No data for {symbol}. Trying TradingView TA fallback...")
                tv_data = get_tradingview_analysis(symbol)
                if tv_data:
                     logger.info(f"TradingView summary for {symbol}: {tv_data['summary']}")
                else:
                    logger.warning(f"No fallback data from TradingView for {symbol}.")     
                # Final filter by original start/end date to ensure consistency across sources
                if start_dt: df = df[df.index >= start_dt]
                if end_dt: df = df[df.index <= end_dt] # Original end_dt, not yf_end + 1 day
                
                # Apply limit if it was the primary constraint and no start_date was given
                if limit and not start_date_iso and len(df) > limit:
                    df = df.tail(limit)

                all_data[symbol] = df
                logger.info(f"✅ Data for {symbol} ({len(df)} rows) from {source}.")
            else:
                logger.warning(f"❌ No data found for {symbol} from any source.")
        
        return all_data

    # --- Helper methods for get_historical_data fallbacks (can be part of the class) ---
    def _map_timeframe_to_finnhub_resolution(self, timeframe: TimeFrame) -> Optional[str]:
        if timeframe.unit == TimeFrameUnit.Minute:
            if timeframe.amount in [1, 5, 15, 30, 60]: return str(timeframe.amount)
        elif timeframe.unit == TimeFrameUnit.Hour and timeframe.amount == 1: return "60"
        elif timeframe.unit == TimeFrameUnit.Day and timeframe.amount == 1: return "D"
        elif timeframe.unit == TimeFrameUnit.Week and timeframe.amount == 1: return "W"
        logger.debug(f"Finnhub: Timeframe {timeframe} not directly mappable.")
        return None

    def _get_finnhub_bars_fallback(self, symbol: str, resolution: str, start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
        if not self._finnhub_client: return pd.DataFrame()
        try:
            start_ts = int(start_dt.timestamp())
            end_ts = int(end_dt.timestamp())
            res = self._finnhub_client.stock_candles(symbol, resolution, start_ts, end_ts)
            if res and res.get('s') == 'ok' and 't' in res and res['t']:
                df = pd.DataFrame(res)
                df['timestamp'] = pd.to_datetime(df['t'], unit='s') # No UTC here, normalize_dataframe handles it
                return df[['timestamp', 'o', 'h', 'l', 'c', 'v']] # Pass timestamp as column
            logger.debug(f"Finnhub: No data for {symbol} (status: {res.get('s', 'unknown') if res else 'N/A'})")
        except finnhub.FinnhubAPIException as e:
            logger.warning(f"Finnhub API Exception for {symbol}: {e}")
        except Exception as e:
            logger.warning(f"General Finnhub fallback error for {symbol}: {e}")
        return pd.DataFrame()

    def _map_timeframe_to_yfinance_interval(self, timeframe: TimeFrame) -> Tuple[Optional[str], Optional[str]]:
        unit_map = {
            TimeFrameUnit.Minute: "m", TimeFrameUnit.Hour: "h", TimeFrameUnit.Day: "d",
            TimeFrameUnit.Week: "wk", TimeFrameUnit.Month: "mo",
        }
        if timeframe.unit in unit_map:
            interval = f"{timeframe.amount}{unit_map[timeframe.unit]}"
            period = "1y" # Default period
            if "m" in interval or "h" in interval:
                if interval == "1m": period = "7d"
                else: period = "60d" # Max for most intraday on yf
            elif "d" in interval or "wk" in interval or "mo" in interval : period = "max"
            return interval, period
        logger.debug(f"yFinance: Timeframe {timeframe} not directly mappable.")
        return None, None


    # --- Streaming Functionality ---
    async def _default_handler(self, data: Any, data_type: str):
        symbol = data.symbol
        ts = pd.Timestamp(data.timestamp, unit='ns', tz='UTC') # Alpaca stream timestamps are nanoseconds

        if data_type == "bar":
            log_msg = f"Stream BAR | {symbol} @ {ts} | O:{data.open} H:{data.high} L:{data.low} C:{data.close} V:{data.volume}"
            self._stream_data_cache["bars"].setdefault(symbol, []).append(data)
        elif data_type == "trade":
            log_msg = f"Stream TRADE | {symbol} @ {ts} | P:{data.price} S:{data.size} Ex:{data.exchange}"
            self._stream_data_cache["trades"].setdefault(symbol, []).append(data)
        elif data_type == "quote":
            log_msg = f"Stream QUOTE | {symbol} @ {ts} | AP:{data.ask_price} BP:{data.bid_price} AS:{data.ask_size} BS:{data.bid_size}"
            self._stream_data_cache["quotes"].setdefault(symbol, []).append(data)
        else:
            log_msg = f"Unknown stream data type: {data_type}"

        logger.debug(log_msg)
        # Limit cache size
        if symbol in self._stream_data_cache.get(data_type + "s", {}): # e.g. self._stream_data_cache["bars"]
            if len(self._stream_data_cache[data_type + "s"][symbol]) > 1000: # Keep last 1000 items
                self._stream_data_cache[data_type + "s"][symbol].pop(0)


    # --- FIX START: De-indent start_stream to make it a class method ---
    async def start_stream(
        self,
        symbols: List[str],
        on_bar: Optional[Callable[[AlpacaBar], Awaitable[Any]]] = None,
        on_trade: Optional[Callable[[AlpacaTrade], Awaitable[Any]]] = None,
        on_quote: Optional[Callable[[AlpacaQuote], Awaitable[Any]]] = None,
        subscribe_bars: bool = True,
        subscribe_trades: bool = True,
        subscribe_quotes: bool = False,
    ): # <--- Correct indentation for a class method
        if not self.is_operational:
            logger.error("Cannot start stream: Alpaca client not operational.")
            return
        if self._websocket_running:
            logger.warning("WebSocket stream is already running. Attempting to stop and restart...")
            await self.stop_stream()  # Allow restart instead of blocking
            if not symbols:
                logger.warning("No symbols provided for streaming.")
                return

        self._stream_data_cache = {"bars": {}, "trades": {}, "quotes": {}}  # Reset cache

        # Async default handlers
        # --- FIX START: Indent default handlers *inside* start_stream ---
        async def default_bar_handler(bar):
             await self._default_handler(bar, "bar")
        async def default_trade_handler(trade):
             await self._default_handler(trade, "trade")
        async def default_quote_handler(quote):
             await self._default_handler(quote, "quote")
        # --- FIX END: Indent default handlers *inside* start_stream ---


        _on_bar = on_bar if on_bar else default_bar_handler
        _on_trade = on_trade if on_trade else default_trade_handler
        _on_quote = on_quote if on_quote else default_quote_handler

        logger.info(f"Starting WebSocket stream for {symbols} (Feed: {self.data_feed}) using base_url: {self.base_url}")
        self._stream = Stream(
            key_id=self.api_key, secret_key=self.secret_key,
            base_url=URL(self.base_url),
            data_feed=self.data_feed,
            raw_data=False
        )

        if subscribe_bars:
            self._stream.subscribe_bars(_on_bar, *symbols)
        if subscribe_trades:
            self._stream.subscribe_trades(_on_trade, *symbols)
        if subscribe_quotes:
            self._stream.subscribe_quotes(_on_quote, *symbols)

        async def run_and_log_exceptions(): # This was already correctly indented
            try:
                logger.info("Stream run_forever task starting...")
                await self._stream._run_forever()
            except asyncio.CancelledError:
                logger.info("Stream run_forever task cancelled.")
            except Exception as e:
                logger.error(f"Stream run_forever task crashed: {e}", exc_info=True)
            finally:
                self._websocket_running = False
                logger.info("Stream run_forever task finished.")

        self._websocket_task = asyncio.create_task(run_and_log_exceptions())
        self._websocket_running = True
        logger.info("✅ WebSocket stream connection initiated.")
    # --- FIX END: De-indent start_stream ---

    async def stop_stream(self):
        if not self._websocket_running or not self._stream:
            logger.info("WebSocket stream not running or not initialized.")
            return
        
        logger.info("Stopping WebSocket stream...")
        try:
            # Unsubscribe from all symbols - current SDK might not have explicit mass unsubscribe.
            # Stopping the websocket is the primary way.
            # For individual: self._stream.unsubscribe_bars(*symbols_list)
            await self._stream.stop_ws() # Gracefully close WebSocket
        except Exception as e:
            logger.error(f"Error during WebSocket stop_ws: {e}")
        
        if self._websocket_task and not self._websocket_task.done():
            self._websocket_task.cancel()
            try:
                await self._websocket_task
            except asyncio.CancelledError:
                logger.info("WebSocket task successfully cancelled.")
            except Exception as e:
                logger.error(f"Exception while awaiting cancelled WebSocket task: {e}")
        
        self._websocket_running = False
        self._stream = None # Release stream object
        self._websocket_task = None
        logger.info("✅ WebSocket stream stopped.")

    def get_stream_cache(self, data_type: str = "bars", symbol: Optional[str] = None) -> Union[List[Any], Dict[str, List[Any]]]:
        """Retrieves cached data from the stream. data_type: 'bars', 'trades', 'quotes'"""
        cache_key = data_type.lower() 
        if cache_key not in self._stream_data_cache:
            return [] if symbol else {}
        
        if symbol:
            return self._stream_data_cache[cache_key].get(symbol, [])
        return self._stream_data_cache[cache_key]

    async def close(self):
        """Closes the connector, stopping any running streams."""
        logger.info("Closing AlpacaConnector...")
        await self.stop_stream()
        # REST client doesn't need explicit closing in this library.
        self.is_operational = False # Mark as no longer operational
        logger.info("AlpacaConnector closed.")


async def example_usage_historical():
    # --- Setup: Assumes secrets are in .streamlit/secrets.toml or passed directly ---
    # Example: ALPACA_API_KEY_PAPER = "YOUR_KEY"
    
    connector = AlpacaConnector(paper=True, feed=DataFeed.IEX) # Uses st.secrets by default if available

    if not connector.is_operational:
        logger.error("Connector not operational. Exiting historical example.")
        return

    logger.info("\n--- Fetching Daily Data (AAPL, MSFT) ---")
    daily_data = connector.get_historical_data(
        tickers=["AAPL", "MSFT", "NONEXISTENTICKER"],
        timeframe_str="1Day",
        start_date_iso="2023-01-01",
        end_date_iso="2023-01-10"
    )
    for symbol, df in daily_data.items():
        logger.info(f"\n{symbol} Daily Data (First 5 rows):")
        if not df.empty: logger.info(df.head())
        else: logger.info("No data.")

    logger.info("\n--- Fetching Intraday Data (SPY) with limit ---")
    # Note: Free IEX data might have limited intraday history
    intraday_data = connector.get_historical_data(
        tickers="SPY",
        timeframe_str="5Min",
        limit=10, # Fetch last 10 available 5-min bars before now
        end_date_iso=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat() # For yesterday to ensure market was open
    )
    if "SPY" in intraday_data and not intraday_data["SPY"].empty:
        logger.info(f"\nSPY 5Min Data (Last 10 bars):\n{intraday_data['SPY']}")
    else:
        logger.info("No SPY intraday data found (check market hours or data availability).")

    await connector.close()


async def example_usage_streaming():
    connector = AlpacaConnector(paper=True, feed=DataFeed.IEX)

    if not connector.is_operational:
        logger.error("Connector not operational. Exiting streaming example.")
        return

    symbols_to_stream = ["AAPL", "MSFT"]
    logger.info(f"\n--- Starting stream for {symbols_to_stream} ---")
    
    # Example of custom handlers (optional)
    async def my_bar_handler(bar: AlpacaBar):
        ts = pd.Timestamp(bar.timestamp, unit='ns', tz='UTC')
        logger.info(f"CUSTOM BAR | {bar.symbol} @ {ts} | C:{bar.close}")
        # connector._stream_data_cache["bars"].setdefault(bar.symbol, []).append(bar) # If you want to also cache

    await connector.start_stream(
        symbols=symbols_to_stream,
        on_bar=my_bar_handler, # Use custom bar handler
        subscribe_trades=False, # Don't need trades for this example
        subscribe_quotes=True   # Let's try quotes
    )

    try:
        await asyncio.sleep(30) # Stream for 30 seconds
    finally:
        logger.info("\n--- Stopping stream ---")
        await connector.stop_stream()
        logger.info("\n--- Stream Cache (Bars AAPL) ---")
        logger.info(connector.get_stream_cache(data_type="bars", symbol="AAPL")[-5:]) # Last 5 cached bars
        logger.info("\n--- Stream Cache (Quotes MSFT) ---")
        logger.info(connector.get_stream_cache(data_type="quotes", symbol="MSFT")[-5:])
        await connector.close()


if __name__ == "__main__":
    # To run these examples, ensure you have your API keys set up
    # (e.g., in .streamlit/secrets.toml or pass them to AlpacaConnector)
    # Example:
    # Create a .streamlit/secrets.toml file:
    # ALPACA_API_KEY_PAPER="PK..."
    # ALPACA_SECRET_KEY_PAPER="sk..."
    # FINNHUB_API_KEY="fk..."
    
    # logging.getLogger('alpaca_trade_api').setLevel(logging.WARNING) # Quieten Alpaca lib logs
    # logging.getLogger('finnhub').setLevel(logging.WARNING)
    # logging.getLogger('yfinance').setLevel(logging.WARNING)


    # asyncio.run(example_usage_historical())
    asyncio.run(example_usage_streaming())