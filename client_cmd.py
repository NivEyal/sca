# client_cmd.py
import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - CLIENT - %(levelname)s - %(message)s')

SERVER_URI = "ws://localhost:8765"

# --- Shared state for responses (can be more sophisticated with message IDs) ---
# For simplicity, we'll just log responses in the main handler for now
# In a real app, you'd use asyncio.Queue or asyncio.Event for synchronization
# if a sender needs to wait for a specific response.

async def message_handler(websocket):
    """Single coroutine to handle ALL incoming messages from the server."""
    try:
        async for message_str in websocket:
            try:
                message = json.loads(message_str)
                msg_type = message.get("type")
                logging.info(f"Received Raw: {message}") # Log all received messages

                if msg_type == "market_data_update":
                    logging.info(f"Market Data Tick: Timestamp: {message.get('timestamp')}, Close: {message.get('data', {}).get('close')}")
                elif msg_type == "market_data_snapshot":
                    logging.info(f"Market Data Snapshot: Timestamp: {message.get('timestamp')}, Close: {message.get('data', {}).get('close')}")
                elif msg_type == "strategy_list":
                    logging.info(f"Strategy List: {message.get('strategies')}")
                    # logging.info(f"Default Params: {message.get('default_params')}") # This can be very long
                elif msg_type == "strategy_result":
                    logging.info(f"Strategy Result for '{message.get('strategy_name')}': Signals: {message.get('signals')}, Params Used: {message.get('params_used')}")
                elif msg_type == "subscription_ack":
                    logging.info(f"Subscription Ack: Feed: {message.get('feed')}, Status: {message.get('status')}")
                elif msg_type == "error":
                    logging.error(f"Server Error Message: {message.get('message')}")
                else:
                    logging.warning(f"Unhandled message type: {msg_type}, Data: {message}")

            except json.JSONDecodeError:
                logging.error(f"Invalid JSON received: {message_str}")
            except Exception as e:
                logging.error(f"Error processing received message: {e} - Message: {message_str}")

    except websockets.exceptions.ConnectionClosedOK:
        logging.info("Connection closed gracefully by server.")
    except websockets.exceptions.ConnectionClosedError as e:
        logging.warning(f"Connection closed with error by server: {e}")
    except Exception as e:
        logging.error(f"Exception in message_handler: {e}")
    finally:
        logging.info("Message handler terminated.")


async def run_cmd_client():
    try:
        async with websockets.connect(SERVER_URI) as websocket:
            logging.info(f"Connected to {SERVER_URI}")

            # Start the single message handler task
            handler_task = asyncio.create_task(message_handler(websocket))

            # --- Test 1: Get Strategies ---
            logging.info("\n--- Test 1: Getting Strategies ---")
            await websocket.send(json.dumps({"type": "get_strategies"}))
            logging.info("Sent: get_strategies request")
            await asyncio.sleep(1) # Give time for response to be processed by handler

            # --- Test 2: Subscribe to Market Data ---
            logging.info("\n--- Test 2: Subscribing to Market Data ---")
            await websocket.send(json.dumps({"type": "subscribe_market_data"}))
            logging.info("Sent: subscribe_market_data request")
            logging.info("Listening for market data for a few seconds (check logs)...")
            await asyncio.sleep(5) # Market data will be logged by message_handler

            # --- Test 3: Run a Strategy with Default Params ---
            logging.info("\n--- Test 3: Running Strategy (Momentum - Default Params) ---")
            await websocket.send(json.dumps({
                "type": "run_strategy",
                "strategy_name": "Momentum Trading",
                "params": {}
            }))
            logging.info("Sent: run_strategy (Momentum) request")
            await asyncio.sleep(1) # Give time for response

            # --- Test 4: Run a Strategy with Custom Params ---
            logging.info("\n--- Test 4: Running Strategy (Scalping - Custom Params) ---")
            await websocket.send(json.dumps({
                "type": "run_strategy",
                "strategy_name": "Scalping (Bollinger Bands)",
                "params": {
                    "bb_period": 15,
                    "bb_std": 2.5
                }
            }))
            logging.info("Sent: run_strategy (Scalping) request")
            await asyncio.sleep(1)

            # --- Test 5: Run a Strategy with List Param ---
            logging.info("\n--- Test 5: Running Strategy (EMA Ribbon MACD - Custom List Param) ---")
            await websocket.send(json.dumps({
                "type": "run_strategy",
                "strategy_name": "EMA Ribbon MACD",
                "params": {
                    "ema_lengths": [10, 20, 30, 40, 60],
                    "macd_fast": 10
                }
            }))
            logging.info("Sent: run_strategy (EMA Ribbon MACD) request")
            await asyncio.sleep(1)

            # --- Test 6: Unsubscribe from Market Data ---
            logging.info("\n--- Test 6: Unsubscribing from Market Data ---")
            await websocket.send(json.dumps({"type": "unsubscribe_market_data"}))
            logging.info("Sent: unsubscribe_market_data request")
            await asyncio.sleep(2) # Allow time for ack and for handler_task to potentially exit if connection closes

            logging.info("\n--- All CMD tests (almost) complete, waiting for handler to finish or connection to close ---")
            # Wait for the handler task to complete (e.g., if connection is closed by server or an error)
            # Or explicitly cancel it after a timeout if the connection is meant to stay open longer
            try:
                await asyncio.wait_for(handler_task, timeout=5.0) # Wait up to 5s for handler to finish
            except asyncio.TimeoutError:
                logging.info("Handler task did not finish in time, cancelling.")
                handler_task.cancel()
            except asyncio.CancelledError:
                 logging.info("Handler task was cancelled.")


    except ConnectionRefusedError:
        logging.error(f"Connection refused. Ensure the WebSocket server ({SERVER_URI}) is running.")
    except websockets.exceptions.InvalidURI:
        logging.error(f"Invalid WebSocket URI: {SERVER_URI}")
    except Exception as e:
        logging.error(f"An unhandled error occurred in run_cmd_client: {e}", exc_info=True)
    finally:
        logging.info("Client script finished.")


if __name__ == "__main__":
    asyncio.run(run_cmd_client())