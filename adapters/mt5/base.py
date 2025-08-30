from typing import Protocol, Any, Dict

class Order(dict):
    pass

class ExecReport(dict):
    pass

class AdapterHealth(dict):
    pass

class BrokerAdapter(Protocol):
    def place_order(self, order: Order) -> ExecReport: ...
    def modify_order(self, order_id: str, **kwargs) -> ExecReport: ...
    def close_all(self) -> None: ...
    def health(self) -> AdapterHealth: ...
