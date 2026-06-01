"""
技术指标本地计算模块

基于 timelyre K 线数据，使用 stockstats 本地计算技术指标。
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from tradingagents.dataflows.providers.china.internal_queries import get_daily_kline

logger = logging.getLogger(__name__)

_INDICATOR_DESC = {
    "close_50_sma": "50 SMA: 中期趋势指标，用于判断趋势方向和动态支撑/阻力位。滞后于价格，需配合更快指标使用。",
    "close_200_sma": "200 SMA: 长期趋势基准，确认整体市场趋势，识别金叉/死叉。反应慢，适合战略性趋势确认。",
    "close_10_ema": "10 EMA: 短期均线，捕捉动量快速变化和潜在入场点。在震荡市中容易产生噪音，需配合更长均线过滤。",
    "macd": "MACD: 通过 EMA 差值计算动量。寻找交叉和背离作为趋势变化信号。低波动或横盘市场需其他指标确认。",
    "macds": "MACD Signal: MACD 线的 EMA 平滑。与 MACD 线交叉触发交易。需作为更广策略的一部分以避免假信号。",
    "macdh": "MACD Histogram: MACD 线与信号线的差值。可视化动量强度，早期发现背离。波动较大，需额外过滤器。",
    "rsi": "RSI: 衡量动量，标记超买/超卖状态。应用70/30阈值并观察背离以发现反转。强趋势中RSI可能持续极端。",
    "boll": "布林中轨: 20 SMA，布林带的基准线。动态价格基准。配合上下轨发现突破或反转。",
    "boll_ub": "布林上轨: 通常为中轨上方2个标准差。信号潜在超买和突破区域。强趋势中价格可能沿上轨运行。",
    "boll_lb": "布林下轨: 通常为中轨下方2个标准差。信号潜在超卖区域。需额外分析避免假反转信号。",
    "atr": "ATR: 平均真实波幅衡量波动率。设置止损水平和调整仓位大小。是反应性指标，作为风险管理策略的一部分。",
    "vwma": "VWMA: 成交量加权移动平均。结合价格行为和成交量确认趋势。注意成交量尖峰导致的偏差。",
    "mfi": "MFI: 资金流量指数，使用价格和成交量衡量买卖压力。>80超买/<20超卖，与RSI/MACD配合确认信号。",
}


def _load_kline_data(symbol: str, curr_date: str, look_back_days: int = 250) -> pd.DataFrame:
    """从 timelyre 加载 K 线数据，足够计算长期指标

    Args:
        symbol: 6位A股代码
        curr_date: 当前日期 YYYY-MM-DD
        look_back_days: 回看天数，默认250个交易日

    Returns:
        包含 OHLCV 数据的 DataFrame
    """
    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    start_dt = curr_dt - timedelta(days=look_back_days * 2)
    start_date = start_dt.strftime("%Y-%m-%d")

    df = get_daily_kline(symbol, start_date, curr_date)

    if df.empty:
        return df

    df = df.rename(columns={
        "trade_day": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
        "turnover": "Amount",
    })

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")
    df = df[df["Date"] <= pd.Timestamp(curr_date)]

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Close"])
    df = df.reset_index(drop=True)

    return df


def calculate_indicators(symbol: str, indicator: str, curr_date: str, look_back_days: int = 30) -> str:
    """计算技术指标并返回格式化报告

    Args:
        symbol: 6位A股代码
        indicator: 技术指标名称或逗号分隔的多个指标
        curr_date: 当前交易日 YYYY-MM-DD
        look_back_days: 回看天数

    Returns:
        格式化的技术指标报告
    """
    indicators = [i.strip().lower() for i in indicator.split(",") if i.strip()]
    results = []

    for ind in indicators:
        try:
            result = _calculate_single_indicator(symbol, ind, curr_date, look_back_days)
            results.append(result)
        except ValueError as e:
            results.append(str(e))

    return "\n\n".join(results)


def _calculate_single_indicator(symbol: str, indicator: str, curr_date: str, look_back_days: int) -> str:
    """计算单个技术指标"""
    if indicator not in _INDICATOR_DESC:
        available = list(_INDICATOR_DESC.keys())
        raise ValueError(f"不支持的指标 '{indicator}'。可用指标: {available}")

    df = _load_kline_data(symbol, curr_date)
    if df.empty:
        return f"{symbol} 无 K 线数据，无法计算 {indicator}"

    close = df["Close"].values.astype(float)
    high = df["High"].values.astype(float) if "High" in df.columns else close
    low = df["Low"].values.astype(float) if "Low" in df.columns else close
    volume = df["Volume"].values.astype(float) if "Volume" in df.columns else np.ones_like(close)
    dates = df["Date"].values

    values = _compute_indicator(indicator, close, high, low, volume)

    curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    before_dt = curr_dt - timedelta(days=look_back_days)

    lines = []
    for i in range(len(dates) - 1, -1, -1):
        dt = pd.Timestamp(dates[i])
        if dt < pd.Timestamp(before_dt):
            break
        date_str = dt.strftime("%Y-%m-%d")
        val = values[i] if i < len(values) else np.nan
        if pd.isna(val):
            lines.append(f"{date_str}: N/A")
        else:
            lines.append(f"{date_str}: {val:.4f}")

    lines.reverse()

    desc = _INDICATOR_DESC.get(indicator, "")
    result_str = (
        f"## {indicator} values from {before_dt.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
        + "\n".join(lines)
        + f"\n\n{desc}"
    )

    return result_str


def _compute_indicator(indicator: str, close: np.ndarray, high: np.ndarray, low: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """根据指标名称计算指标值数组

    Args:
        indicator: 指标名称
        close: 收盘价数组
        high: 最高价数组
        low: 最低价数组
        volume: 成交量数组

    Returns:
        与 close 等长的指标值数组
    """
    n = len(close)
    result = np.full(n, np.nan)

    if indicator == "close_10_ema":
        period = 10
        result = _ema(close, period)

    elif indicator == "close_50_sma":
        period = 50
        result = _sma(close, period)

    elif indicator == "close_200_sma":
        period = 200
        result = _sma(close, period)

    elif indicator == "rsi":
        period = 14
        result = _rsi(close, period)

    elif indicator in ("macd", "macds", "macdh"):
        macd_line, signal_line, hist = _macd(close)
        if indicator == "macd":
            result = macd_line
        elif indicator == "macds":
            result = signal_line
        else:
            result = hist

    elif indicator in ("boll", "boll_ub", "boll_lb"):
        mid, upper, lower = _bollinger(close)
        if indicator == "boll":
            result = mid
        elif indicator == "boll_ub":
            result = upper
        else:
            result = lower

    elif indicator == "atr":
        period = 14
        result = _atr(high, low, close, period)

    elif indicator == "vwma":
        period = 20
        result = _vwma(close, volume, period)

    elif indicator == "mfi":
        period = 14
        result = _mfi(high, low, close, volume, period)

    return result


def _sma(data: np.ndarray, period: int) -> np.ndarray:
    result = np.full_like(data, np.nan, dtype=float)
    if len(data) < period:
        return result
    cumsum = np.cumsum(data)
    result[period - 1:] = (cumsum[period - 1:] - np.concatenate([[0], cumsum[:-period]])) / period
    return result


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    result = np.full_like(data, np.nan, dtype=float)
    if len(data) < period:
        return result
    multiplier = 2.0 / (period + 1)
    result[period - 1] = np.mean(data[:period])
    for i in range(period, len(data)):
        result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
    return result


def _rsi(data: np.ndarray, period: int = 14) -> np.ndarray:
    result = np.full_like(data, np.nan, dtype=float)
    if len(data) < period + 1:
        return result
    deltas = np.diff(data)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, len(data)):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        if avg_loss == 0:
            result[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i] = 100.0 - (100.0 / (1.0 + rs))

    return result


def _macd(data: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = _ema(data, fast)
    ema_slow = _ema(data, slow)
    macd_line = ema_fast - ema_slow
    valid_mask = ~np.isnan(macd_line)
    signal_line = np.full_like(data, np.nan, dtype=float)
    if np.sum(valid_mask) >= signal:
        valid_idx = np.where(valid_mask)[0]
        valid_macd = macd_line[valid_mask]
        sig = _ema(valid_macd, signal)
        for i, idx in enumerate(valid_idx):
            signal_line[idx] = sig[i]
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bollinger(data: np.ndarray, period: int = 20, std_dev: float = 2.0):
    mid = _sma(data, period)
    upper = np.full_like(data, np.nan, dtype=float)
    lower = np.full_like(data, np.nan, dtype=float)
    for i in range(period - 1, len(data)):
        window = data[i - period + 1:i + 1]
        std = np.std(window, ddof=0)
        upper[i] = mid[i] + std_dev * std
        lower[i] = mid[i] - std_dev * std
    return mid, upper, lower


def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    result = np.full(n, np.nan, dtype=float)
    if n < 2:
        return result
    tr = np.maximum(high[1:] - low[1:], np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    tr = np.concatenate([[high[0] - low[0]], tr])
    if len(tr) < period:
        return result
    result[period - 1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        result[i] = (result[i - 1] * (period - 1) + tr[i]) / period
    return result


def _vwma(close: np.ndarray, volume: np.ndarray, period: int = 20) -> np.ndarray:
    result = np.full_like(close, np.nan, dtype=float)
    if len(close) < period:
        return result
    for i in range(period - 1, len(close)):
        pv = np.sum(close[i - period + 1:i + 1] * volume[i - period + 1:i + 1])
        v = np.sum(volume[i - period + 1:i + 1])
        result[i] = pv / v if v != 0 else np.nan
    return result


def _mfi(high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    result = np.full(n, np.nan, dtype=float)
    if n < period + 1:
        return result
    tp = (high + low + close) / 3.0
    mf = tp * volume
    pos_mf = np.where(tp[1:] > tp[:-1], mf[1:], 0.0)
    neg_mf = np.where(tp[1:] < tp[:-1], mf[1:], 0.0)
    for i in range(period, n):
        pos_sum = np.sum(pos_mf[i - period:i])
        neg_sum = np.sum(neg_mf[i - period:i])
        if neg_sum == 0:
            result[i] = 100.0
        else:
            mfi_val = 100.0 - (100.0 / (1.0 + pos_sum / neg_sum))
            result[i] = mfi_val
    return result
