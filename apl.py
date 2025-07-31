from alpaca_data import AlpacaConnector

# Replace with your working keys
API_KEY = "AK2V88RDO5MYCFOE8FJH"
SECRET_KEY = "gmCM49z9z3VlmTnoF7vsn9wliXZz6SE6NHCs5d5I"
BASE_URL = "https://api.alpaca.markets"
DATA_FEED = "iex"
PAPER_TRADING = False

if __name__ == "__main__":
    connector = AlpacaConnector(
        api_key=API_KEY,
        secret_key=SECRET_KEY,
        paper=PAPER_TRADING,
        feed=DATA_FEED,
        base_url_override=BASE_URL
    )

    if connector.is_operational:
        print("✅ Alpaca REST connection is operational.")
        connector.test_rest_data_fetch("AAPL")
    else:
        print("❌ Alpaca connection failed. Check logs.")
