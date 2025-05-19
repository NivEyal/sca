import logging
from alpaca_trade_api.rest import REST
from alpaca_trade_api.stream import Stream
import asyncio
import sys
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Hard-coded Alpaca API credentials from secrets.toml
API_KEY = "AKNBUFB8HJFN2XTQWXSK"
SECRET_KEY = "hSQOdDX7A1Ujj65N9nzE3qikNNUyNceKWGaolbmK"
DATA_FEED = "iex"  # From APCA_DATA_FEED
PAPER_TRADING = False  # From APCA_PAPER
BASE_URL = "https://paper-api.alpaca.markets" if PAPER_TRADING else "https://api.alpaca.markets"

def test_rest_connection(api_key, secret_key, base_url, data_feed):
    """Test REST API connection and data fetch."""
    logger.info(f"Testing REST API connection (Base URL: {base_url}, Feed: {data_feed})")
    
    try:
        # Initialize REST client
        rest_client = REST(
            key_id=api_key,
            secret_key=secret_key,
            base_url=base_url
        )
        
        # Test authentication with account info
        logger.info("Attempting to fetch account information...")
        account = rest_client.get_account()
        logger.info(f"✅ Account authentication successful. Account ID: {account.id}, Status: {account.status}")
        
        # Test data fetch (1-minute bars for AAPL)
        logger.info(f"Attempting to fetch sample data (1Min bars for AAPL, Feed: {data_feed})...")
        bars = rest_client.get_bars(
            symbol="AAPL",
            timeframe="1Min",
            limit=1,
            feed=data_feed
        ).df
        
        if not bars.empty:
            logger.info(f"✅ Data fetch successful. Received {len(bars)} bar(s) for AAPL")
            logger.debug(f"Sample bar: {bars.iloc[0].to_dict()}")
        else:
            logger.warning("Data fetch returned no bars")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ REST API test failed: {e}")
        if "forbidden" in str(e).lower() or "subscription" in str(e).lower():
            logger.error(f"Possible issue: Account may not have access to '{data_feed}' feed")
        elif "authorized" in str(e).lower():
            logger.error("Possible issue: Invalid or unauthorized API keys")
        return False

async def test_websocket_connection(api_key, secret_key, data_feed, symbols=["AAPL"]):
    """Test WebSocket streaming connection."""
    logger.info(f"Testing WebSocket connection (Feed: {data_feed}, Symbols: {symbols})")
    
    try:
        # Initialize Stream client
        stream = Stream(
            key_id=api_key,
            secret_key=secret_key,
            data_feed=data_feed,
            raw_data=False
        )
        
        # Define handlers
        async def handle_bar(bar):
            logger.info(f"Received bar for {bar.symbol}: Close={bar.close}, Time={bar.timestamp}")
        
        async def handle_trade(trade):
            logger.info(f"Received trade for {trade.symbol}: Price={trade.price}, Size={trade.size}")
        
        # Subscribe to streams
        for symbol in symbols:
            stream.subscribe_bars(handle_bar, symbol)
            stream.subscribe_trades(handle_trade, symbol)
        
        # Run stream for 10 seconds to test
        logger.info("Starting WebSocket stream for 10 seconds...")
        stream_task = asyncio.create_task(stream._run_forever())
        
        # Wait for 10 seconds to collect some data
        await asyncio.sleep(10)
        
        # Stop the stream
        logger.info("Stopping WebSocket stream...")
        await stream.stop_ws()
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass
        
        logger.info("✅ WebSocket test completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"❌ WebSocket test failed: {e}")
        if "forbidden" in str(e).lower() or "subscription" in str(e).lower():
            logger.error(f"Possible issue: Account may not have access to '{data_feed}' feed")
        return False

async def main():
    """Main function to run all tests."""
    # Log configuration
    logger.info(f"Configuration: Paper Trading={PAPER_TRADING}, Data Feed={DATA_FEED}, Base URL={BASE_URL}")
    
    # Validate configuration
    if API_KEY == "placeholder_api_key" or SECRET_KEY == "placeholder_secret_key":
        logger.error("Invalid API keys. Please update the hard-coded API_KEY and SECRET_KEY.")
        return
    
    if DATA_FEED not in ["sip", "iex"]:
        logger.error(f"Invalid data feed: {DATA_FEED}. Must be 'sip' or 'iex'.")
        logger.info("Please update the hard-coded DATA_FEED to 'iex' or 'sip'.")
        return
    
    # Run REST test
    rest_success = test_rest_connection(API_KEY, SECRET_KEY, BASE_URL, DATA_FEED)
    
    # Run WebSocket test
    ws_success = await test_websocket_connection(API_KEY, SECRET_KEY, DATA_FEED)
    
    # Summary
    logger.info("\n=== Test Summary ===")
    if rest_success and ws_success:
        logger.info("✅ All tests passed! Alpaca API connection is fully operational.")
    else:
        logger.error("❌ One or more tests failed. Check logs for details.")
        if not rest_success:
            logger.error("REST API test failed. Verify API keys and account status.")
        if not ws_success:
            logger.error("WebSocket test failed. Verify data feed access and subscription.")
        logger.info("Next steps:")
        logger.info("- Log in to Alpaca dashboard (https://app.alpaca.markets) and verify API keys under Paper Trading.")
        logger.info("- Ensure account has access to the IEX data feed.")
        logger.info("- If keys are invalid, regenerate new keys and update the script.")
        logger.info("- If IEX feed is not accessible, contact Alpaca support or try setting DATA_FEED to 'sip'.")

if __name__ == "__main__":
    # Ensure asyncio runs correctly
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")