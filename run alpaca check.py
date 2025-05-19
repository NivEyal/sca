from alpaca_data import AlpacaConnector

# Replace with your working keys
API_KEY = "AKNBUFB8HJFN2XTQWXSK"
SECRET_KEY = "hSQOdDX7A1Ujj65N9nzE3qikNNUyNceKWGaolbmK"
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
