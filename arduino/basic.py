import serial

class ArduinoLEDService:
    def __init__(self, port='COM3', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        try:
            self.arduino = serial.Serial(self.port, self.baudrate, timeout=1)
        except Exception:
            self.arduino = None

    def led_on(self, bin_id: str, picker_color: str):
        if self.arduino:
            cmd = f"BIN_{bin_id}_{picker_color}\n"
            self.arduino.write(cmd.encode())

    def led_off(self, bin_id: str, picker_color: str):
        if self.arduino:
            cmd = f"BIN_{bin_id}_{picker_color}_OFF\n"
            self.arduino.write(cmd.encode())

arduino_service = ArduinoLEDService()