import serial
import time

class GateController:
    def __init__(self, port='/dev/cu.usbmodem1101'):  # Mac port format
        try:
            self.arduino = serial.Serial(port, 9600, timeout=1)
            time.sleep(2)  # Wait for Arduino to reset
        except serial.SerialException:
            print(f"Could not open port {port}")
            self.arduino = None

    def open_gate(self):
        if self.arduino:
            self.arduino.write(b'OPEN\n')
            return True
        return False

    def trigger_buzzer(self):
        if self.arduino:
            self.arduino.write(b'BUZZ\n')
            return True
        return False