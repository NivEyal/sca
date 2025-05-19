import logging
import asyncio
import pandas as pd
from alpaca_trade_api.rest import REST
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.common import URL
from typing import List, Dict, Optional, Callable, Any
from enum import Enum
from datetime import datetime
from finnhub_fallback import get_finnhub_bars
import yfinance as yf

# --- Logging ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --- Feed Enum ---
class DataFeed(str, Enum):
    SIP = "sip"
    IEX = "iex"

class AlpacaConnector:
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        paper: bool = False,
        feed: str = DataFeed.IEX,
        base_url: str = "https://api.alpaca.markets"
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper_trading = paper
        self.data_feed = feed.lower()
        self.base_url = base_url

        self._rest_client: Optional[REST] = None
        self._stream: Optional[Stream] = None
        self._websocket_task: Optional[asyncio.Task] = None
        self._websocket_running = False
        self._stream_data_cache = {"bars": {}, "trades": {}}
        self.is_operational = False

        self._initialize_rest_client()

    def fetch_yf_fallback(self, symbol: str, period="5d", interval="1d") -> Optional[pd.DataFrame]:
        try:
            df = yf.download(symbol, period=period, interval=interval, progress=False)
            if not df.empty:
                df.columns = df.columns.str.lower()
                df.index = df.index.tz_localize("UTC") if df.index.tz is None else df.index.tz_convert("UTC")
                return df
        except Exception as e:
            logger.warning(f"Yahoo Finance fallback failed for {symbol}: {e}")
        return None

    def _initialize_rest_client(self):
        logger.info(f"Initializing REST client (Paper: {self.paper_trading}, Feed: {self.data_feed})")
        try:
            self._rest_client = REST(
                key_id=self.api_key,
                secret_key=self.secret_key,
                base_url=self.base_url
            )
            account = self._rest_client.get_account()
            logger.info(f"✅ Authenticated. Account status: {account.status}, ID: {account.id}")
            self.is_operational = True
        except Exception as e:
            logger.error(f"❌ Failed to initialize REST client: {e}")
            self.is_operational = False

    def get_historical_data(
        self,
        tickers: List[str],
        timeframe_str: str = "1Min",
        limit_per_symbol: int = 300
    ) -> Dict[str, pd.DataFrame]:
        data = {}

        for symbol in tickers:
            try:
                bars = self._rest_client.get_bars(
                    symbol=symbol,
                    timeframe=timeframe_str,
                    limit=limit_per_symbol,
                    feed=self.data_feed
                ).df

                if bars.empty and "Min" in timeframe_str:
                    logger.warning(f"No Alpaca bars for {symbol}. Trying Finnhub fallback.")
                    fallback = get_finnhub_bars(symbol, resolution="1", limit=limit_per_symbol)
                    if not fallback.empty:
                        data[symbol] = fallback
                        continue

                if bars.empty:
                    logger.warning(f"No bars returned for {symbol}, trying yFinance fallback.")
                    yf_data = self.fetch_yf_fallback(symbol)
                    if yf_data is not None and not yf_data.empty:
                        data[symbol] = yf_data
                        continue
                    logger.warning(f"No fallback data for {symbol}.")
                    continue

                bars.columns = bars.columns.str.lower()
                if not isinstance(bars.index, pd.DatetimeIndex):
                    bars.index = pd.to_datetime(bars.index, utc=True)
                elif bars.index.tz is None:
                    bars.index = bars.index.tz_localize("UTC")
                else:
                    bars.index = bars.index.tz_convert("UTC")

                data[symbol] = bars

            except Exception as e:
                logger.error(f"Error fetching {symbol} from Alpaca. Trying Finnhub fallback. Error: {e}")
                fallback = get_finnhub_bars(symbol, resolution="1", limit=limit_per_symbol)
                if not fallback.empty:
                    data[symbol] = fallback

        return data

    def get_latest_trade(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            trade = self._rest_client.get_latest_trade(symbol)
            return {
                "price": trade.price,
                "timestamp": trade.timestamp
            }
        except Exception as e:
            logger.error(f"Error getting latest trade for {symbol}: {e}")
            return None

    async def _default_bar_handler(self, bar):
        logger.info(f"Bar | {bar.symbol} | C={bar.close} | V={bar.volume}")
        self._stream_data_cache["bars"].setdefault(bar.symbol, []).append(bar)

    async def _default_trade_handler(self, trade):
        logger.info(f"Trade | {trade.symbol} | P={trade.price} | S={trade.size}")
        self._stream_data_cache["trades"].setdefault(trade.symbol, []).append(trade)

    async def start_stream(
        self,
        symbols: List[str],
        on_bar: Optional[Callable] = None,
        on_trade: Optional[Callable] = None
    ):
        if not self.is_operational:
            logger.error("Cannot start stream: REST client not operational.")
            return
        if self._websocket_running:
            logger.warning("WebSocket already running.")
            return
        if not symbols:
            logger.warning("No symbols provided.")
            return

        bar_handler = on_bar or self._default_bar_handler
        trade_handler = on_trade or self._default_trade_handler

        self._stream = Stream(
            key_id=self.api_key,
            secret_key=self.secret_key,
            base_url=URL(self.base_url),
            data_feed=self.data_feed,
            raw_data=False
        )

        for symbol in symbols:
            self._stream.subscribe_bars(bar_handler, symbol)
            self._stream.subscribe_trades(trade_handler, symbol)

        self._websocket_task = asyncio.create_task(self._stream._run_forever())
        self._websocket_running = True
        logger.info("✅ WebSocket stream started.")

    async def stop_stream(self):
        if not self._websocket_running or not self._stream:
            return
        logger.info("Stopping WebSocket...")
        await self._stream.stop_ws()
        if self._websocket_task:
            self._websocket_task.cancel()
            try:
                await self._websocket_task
            except asyncio.CancelledError:
                pass
        self._websocket_running = False
        logger.info("✅ WebSocket stopped.")

    async def close(self):
        await self.stop_stream()
        logger.info("AlpacaConnector closed.")
