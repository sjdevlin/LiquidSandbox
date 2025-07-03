from tokenize import String
from serial import Serial
from time import sleep
from services import Logger, AppConfig
from abc import ABC, abstractmethod

class Stage(ABC):
    """Abstract base class defining the interface for all cameras."""

    def __init__(self, port, parity, baudrate, stopbits, bytesize, timeout):
        
        self.logger = Logger() # Singleton instance
        self.my_app_config = AppConfig()  # Singleton instance - may be opened multiple times from different classes

    @abstractmethod
    def move_x(self, distance):
        pass

    @abstractmethod
    def get_x(self):
        pass



class OlympusStageController(Stage):

    def __init__(self):

        self.port = self.my_app_config.get("stage_port")
        self.baudrate = self.my_app_config.get("stage_baudrate")
        self.parity = self.my_app_config.get("stage_parity")
        self.stopbits = self.my_app_config.get("stage_stopbits")
        self.bytesize = self.my_app_config.get("stage_bytesize")
        self.timeout = self.my_app_config.get("stage_timeout")

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
                self.logger.debug(f"Connected to stage.")
                return True
            else:
                return False
        except Exception as e:
            self.logger.error(f"Error connecting to stage: {e}")
            return False


    def send_command(self, command):
        self.ser.write((command + '\n').encode())

    def read_response(self):
        return self.ser.readline().decode().strip()

    def move_x(self, distance):
        pass

    def move_y(self, distance):
        pass

    def set_speed(self, speed):
        pass

    def get_x(self):
        pass

    def get_y(self):
        pass



class TemikaStageController(Stage):

    def __init__(self):
        from hardware import TemikaComms
        self.temika_comms = TemikaComms()
        self.my_app_config = AppConfig()  # Singleton instance - may be opened multiple times from different classes
        self.logger = Logger()
        self.name = self.my_app_config.get("temika_name")


    def move_x(self, position, speed):
        command = f"<{self.name}>"
        command += "<stepper axis=\"x\">"
        command += f"<move_absolute>{position} {speed}</move_absolute>"
        command += "<wait_moving_end></wait_moving_end>"
        command += "</stepper>"
        command += f"</{self.name}>"
        reply = self.temika_comms.send_command(command, wait_for="Done")
        print (self.get_x())

    def move_xy(self, x_position, y_position, speed):#TODO check with Temika if this is correct
        command = f"<{self.name}>"
        command += "<stepper axis=\"x\">"
        command += f"<move_absolute>{x_position} {speed}</move_absolute>"
        command += f"<move_absolute>{y_position} {speed}</move_absolute>"
        command += "<wait_moving_end></wait_moving_end>"
        command += "</stepper>"
        command += f"</{self.name}>"
        reply = self.temika_comms.send_command(command, reply=False)
        print (reply)
        print ("new line\n")
        print (self.get_x())


    def move_y(self, distance):
        pass

    def set_speed(self, speed):
        pass

    def get_x(self):
        command = f"<{self.name}>"
        command += "<stepper axis=\"x\">"
        command += "<status></status>"
        command += "</stepper>"
        command += f"</{self.name}>"
        reply = self.temika_comms.send_command('</stepper>',wait_for="status")

        if "status" in reply:
            parts = reply.split("status ")
            if len(parts) > 1:
                x_pos = float(parts[1].split()[0])
            else:
                x_pos = 0.0
        else:
            self.logger.error("No status found in reply, returning 0.0 x position.")
            x_pos = 0.0
        return x_pos

    def get_y(self):
        command = f"<{self.name}>"
        command += "<stepper axis=\"y\">"
        command += "<status></status>"
        command += "</stepper>"
        command += f"</{self.name}>"
        reply = self.temika_comms.send_command('</stepper>',wait_for="status")
        
        if "status" in reply:
            parts = reply.split("status ")
            if len(parts) > 1:
                y_pos = float(parts[1].split()[0])
            else:
                y_pos = 0.0
        else:
            self.logger.error("No status found in reply, returning 0.0 y position.")
            y_pos = 0.0
        return y_pos

class StageControllerFactory:

    @staticmethod
    def create_stage_controller():
        logger = Logger() # Singleton instance
        my_app_config = AppConfig()  # Singleton instance - may be opened multiple times from different classes
        stage_type = my_app_config.get("stage_type")

        if stage_type == "Olympus":
            return OlympusStageController()
        elif stage_type == "Temika":
            return TemikaStageController()
        else:
            logger.error(f"Unknown stage type: {stage_type}")
            return None
