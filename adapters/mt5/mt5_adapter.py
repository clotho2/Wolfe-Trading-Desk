from .base import BrokerAdapter, Order, ExecReport, AdapterHealth

class MT5Adapter(BrokerAdapter):
    def place_order(self, order: Order) -> ExecReport:
        return ExecReport(status="DRY_RUN", order=order)

    def modify_order(self, order_id: str, **kwargs) -> ExecReport:
        return ExecReport(status="DRY_RUN", order_id=order_id, changes=kwargs)

    def close_all(self) -> None:
        return None

    def health(self) -> AdapterHealth:
        return AdapterHealth(status="ok")
