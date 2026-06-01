"""
统一股票数据提供器基类
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, date
import logging
import pandas as pd


class BaseStockDataProvider(ABC):

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.connected = False
        self.logger = logging.getLogger(f"{__name__}.{provider_name}")

    @abstractmethod
    async def connect(self) -> bool:
        pass

    async def disconnect(self):
        self.connected = False

    def is_available(self) -> bool:
        return self.connected

    @abstractmethod
    async def get_stock_basic_info(self, symbol: str = None) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        pass

    @abstractmethod
    async def get_stock_quotes(self, symbol: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        start_date: Union[str, date],
        end_date: Union[str, date] = None
    ) -> Optional[pd.DataFrame]:
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.provider_name}', connected={self.connected})>"
