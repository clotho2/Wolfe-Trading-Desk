# Watchlist Configuration

## Current Configuration
The watchlist has been trimmed to focus on three major currency pairs:
- **EURUSD** - Euro/US Dollar
- **USDCHF** - US Dollar/Swiss Franc  
- **NZDUSD** - New Zealand Dollar/US Dollar

## Configuration Files

### 1. Main Configuration: `config/default.yaml`
The watchlist is defined in lines 36-47. Currently active pairs are uncommented, while the expanded list is preserved as comments for future use.

### 2. Environment Override: `.env`
The `EXECUTOR_MODE` is set to `LIVE` for production trading.

## last_tick() Functionality

The `last_tick()` function is implemented in the MT5 adapter (`adapters/mt5/mt5_adapter.py`) and provides:
- Timestamp of the last received market tick
- Connection status monitoring
- Watchlist subscription verification

### Access Points:
1. **Direct via Adapter**: `adapter.last_tick` attribute
2. **Status Method**: `adapter.get_status()` returns full status including last_tick
3. **API Endpoint**: `GET /adapter/mt5/status` (when server is running)

## Expanding the Watchlist

To add more currency pairs in the future:

1. Edit `config/default.yaml` (lines 41-47)
2. Uncomment desired pairs or add new ones:
   ```yaml
   watchlist:
     - EURUSD
     - USDCHF
     - NZDUSD
     - AUDCAD    # Uncomment to add
     - CADCHF    # Uncomment to add
     # Add more pairs as needed
   ```

3. Restart the application to apply changes

## Available Symbols (Common)
The MT5 adapter recognizes these symbols:
- Forex: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURJPY, GBPJPY, EURGBP
- Commodities: XAUUSD (Gold), XAGUSD (Silver)
- Indices: US30, US100, US500, DE30, UK100, JP225
- Crypto: BTCUSD, ETHUSD

## Testing
After modifying the watchlist:
1. Check configuration loads correctly
2. Verify MT5 adapter subscribes to all symbols
3. Confirm last_tick() updates for active symbols
4. Monitor logs for any missing symbol warnings