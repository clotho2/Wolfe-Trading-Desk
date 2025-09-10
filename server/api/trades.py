# path: server/api/trades.py
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from config.settings import settings
from core.executor.registry import get_adapter

router = APIRouter(prefix="/trades", tags=["trades"])


def read_shadow_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Read recent shadow log entries for trade visualization."""
    shadow_dir = Path("logs/shadow")
    if not shadow_dir.exists():
        return []
    
    all_entries = []
    # Get all shadow log files, sorted by date (most recent first)
    log_files = sorted(shadow_dir.glob("shadow-*.jsonl"), reverse=True)
    
    for log_file in log_files[:3]:  # Check last 3 days of logs
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        all_entries.append(entry)
        except Exception:
            continue
    
    # Sort by timestamp and return most recent
    all_entries.sort(key=lambda x: x.get('ts', ''), reverse=True)
    return all_entries[:limit]


def read_event_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Read recent event logs for trade activity."""
    events_file = Path("logs/events.jsonl")
    if not events_file.exists():
        return []
    
    entries = []
    try:
        with open(events_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass
    
    # Return most recent entries
    return entries[-limit:] if len(entries) > limit else entries


@router.get("/feed")
async def get_trade_feed(limit: int = Query(50, ge=1, le=500)):
    """Get recent trade activity feed."""
    # Combine shadow logs and event logs
    shadow_logs = read_shadow_logs(limit)
    event_logs = read_event_logs(limit)
    
    # Format trades for display
    trades = []
    
    # Process shadow logs (simulated trades)
    for log in shadow_logs:
        if log.get('op') == 'place_order':
            payload = log.get('payload', {})
            trades.append({
                'timestamp': log.get('ts'),
                'type': 'order',
                'action': 'place',
                'symbol': payload.get('symbol'),
                'side': payload.get('side'),
                'qty': payload.get('qty'),
                'mode': 'SHADOW',
                'status': 'simulated'
            })
        elif log.get('op') == 'close_all':
            trades.append({
                'timestamp': log.get('ts'),
                'type': 'close',
                'action': 'close_all',
                'mode': 'SHADOW',
                'status': 'simulated'
            })
    
    # Process event logs
    for log in event_logs:
        event_type = log.get('event')
        if event_type in ['trade_placed', 'position_closed', 'order_modified']:
            trades.append({
                'timestamp': log.get('timestamp', log.get('ts')),
                'type': event_type,
                'data': log.get('data', {}),
                'mode': log.get('mode', 'UNKNOWN')
            })
    
    # Sort by timestamp
    trades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return JSONResponse(content={'trades': trades[:limit]})


@router.get("/positions")
async def get_positions():
    """Get current open positions."""
    adapter = get_adapter("mt5")
    
    if not adapter:
        return JSONResponse(content={'positions': [], 'error': 'Adapter not available'})
    
    # Try to get positions from adapter
    positions = []
    try:
        if hasattr(adapter, 'list_open_positions'):
            pos_list = await adapter.list_open_positions()
            for p in pos_list:
                positions.append({
                    'symbol': p.symbol if hasattr(p, 'symbol') else 'UNKNOWN',
                    'ticket': p.ticket if hasattr(p, 'ticket') else 0,
                    'side': getattr(p, 'side', 'UNKNOWN'),
                    'volume': getattr(p, 'volume', 0),
                    'profit': getattr(p, 'profit', 0)
                })
    except Exception as e:
        return JSONResponse(content={'positions': [], 'error': str(e)})
    
    # Also check the adapter's book for DRY_RUN mode
    if hasattr(adapter, '_book'):
        for symbol, qty in adapter._book.items():
            if qty != 0:
                positions.append({
                    'symbol': symbol,
                    'ticket': 0,
                    'side': 'BUY' if qty > 0 else 'SELL',
                    'volume': abs(qty),
                    'profit': 0,
                    'mode': 'DRY_RUN'
                })
    
    return JSONResponse(content={'positions': positions})


@router.get("/stats")
async def get_trading_stats():
    """Get trading statistics and metrics."""
    # Calculate basic stats from logs
    trades = read_shadow_logs(1000) + read_event_logs(1000)
    
    total_trades = len([t for t in trades if t.get('op') == 'place_order' or t.get('event') == 'trade_placed'])
    
    # Get mode and adapter status
    adapter = get_adapter("mt5")
    adapter_status = adapter.get_status() if adapter and hasattr(adapter, 'get_status') else {}
    
    stats = {
        'total_trades_today': total_trades,
        'mode': settings.EXECUTOR_MODE.value if hasattr(settings.EXECUTOR_MODE, 'value') else str(settings.EXECUTOR_MODE),
        'adapter_connected': adapter_status.get('connected', False),
        'watchlist_count': len(settings.watchlist) if hasattr(settings, 'watchlist') else 0,
        'daily_dd_limit': f"{settings.DAILY_HARD_DD_PCT * 100:.1f}%",
        'soft_freeze_limit': f"{settings.DAILY_SOFT_FREEZE_PCT * 100:.1f}%",
        'order_rate_cap': f"{settings.ORDER_RATE_CAP_PER_60S}/min",
        'risk_mode': settings.RISK_MODE
    }
    
    return JSONResponse(content=stats)


@router.get("/watchlist")
async def get_watchlist():
    """Get current watchlist symbols."""
    watchlist = settings.watchlist if hasattr(settings, 'watchlist') else []
    
    # Get adapter to check subscribed symbols
    adapter = get_adapter("mt5")
    subscribed = []
    if adapter and hasattr(adapter, 'watchlist_symbols'):
        subscribed = list(adapter.watchlist_symbols)
    
    return JSONResponse(content={
        'configured': watchlist,
        'subscribed': subscribed,
        'count': len(watchlist)
    })