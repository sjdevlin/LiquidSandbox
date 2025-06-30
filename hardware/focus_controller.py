from tokenize import String
from serial import Serial
from time import sleep
from services import Logger, AppConfig
from abc import ABC, abstractmethod

class Focus(ABC):
    """Abstract base class defining the interface for all cameras."""

    def __init__(self, port, parity, baudrate, stopbits, bytesize, timeout):
        
        self.logger = Logger() # Singleton instanceself.
        self.my_app_config = AppConfig()  # Singleton instance - may be opened multiple times from different classes

    @abstractmethod
    def move_z(self, distance):
        pass

    def get_z(self):
        pass



class OlympusX81FocusController(Focus):

    def __init__(self):

        self.port = self.my_app_config.get("focus_port")
        self.baudrate = self.my_app_config.get("focus_baudrate")
        self.parity = self.my_app_config.get("focus_parity")
        self.stopbits = self.my_app_config.get("focus_stopbits")
        self.bytesize = self.my_app_config.get("focus_bytesizeself.")
        self.timeout = self.my_app_config.get("focus_timeout")

    def connect(self):
        try:
            self.ser = Serial(
                        port=self.port,
                        baudrate=self.baudrate,
                        parity=self.parity,
                        stopbits=self.stopbits,
                        bytesize=self.bytesize,
                        timeout=self.timeout)

            if self.ser.is_open:
                self.logger.debug(f"Connected to Olympus focus.")
                return True
            else:
                return False
        except Exception as e:
            self.logger.error(f"Error connecting to Olympus focus: {e}")
            return False


    def send_command(self, command):
        self.ser.write((command + '\n').encode())

    def read_response(self):
        return self.ser.readline().decode().strip()

    def move_z(self, distance):
        pass

    def get_z(self):
        pass


class TemikaFocusController(Focus):

    def __init__(self):
        from hardware import TemikaComms
        self.temika_comms = TemikaComms()

        
    def autofocus(self, status=False):
        afocus_status = "ON" if status else "OFF"
        command = "<afocus>\n"
        command += f"\t<enable>{afocus_status}</enable>\n"
        command += "\t<wait_lock>0.2 10.3</wait_lock>\n" if status else ""
        command += "</afocus>\n"
        self.send_command(command)
        self.logger.debug(f"Autofocus set to {afocus_status}")


    def move_z(self, distance):
        pass

    def get_z(self):
        command = "<stepper axis=\"z\">"
        command += "<status></status>"
        command += "</stepper>"
        reply = self.temika_comms.send_command(command,True)
        z_pos = float(reply.split()[3]) if len(reply.split()) > 3 else 0.0
        return z_pos


class FocusControllerFactory:

    @staticmethod
    def create_focus_controller():
        logger = Logger() # Singleton instance
        my_app_config = AppConfig()  # Singleton instanceself. - may be opened multiple times from different classes
        focus_type = my_app_config.get("focus_type")

        if focus_type == "OlympusX81":
            return OlympusX81FocusController()
        elif focus_type == "Temika":
            return TemikaFocusController()
        else:
            logger.error(f"Unknown stage type: {focus_type}")
            return None
