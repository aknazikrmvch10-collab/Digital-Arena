from .base import BaseDriver
from .mock import MockDriver
from .standalone import StandaloneDriver
from .icafe import ICafeDriver
from .runpad import RunpadDriver
# from .smartshell import SmartShellDriver (Future)

class DriverFactory:
    @staticmethod
    def get_driver(driver_type: str, config: dict) -> BaseDriver:
        if driver_type == "MOCK":
            return MockDriver(config)
        elif driver_type == "ICAFE":
            return ICafeDriver(config)
        elif driver_type == "RUNPAD":
            return RunpadDriver(config)
        elif driver_type == "STANDALONE":
            return StandaloneDriver(config)
        elif driver_type == "SMARTSHELL":
            # return SmartShellDriver(config)
            raise NotImplementedError("SmartShell driver not yet implemented")
        else:
            raise ValueError(f"Unknown driver type: {driver_type}")

