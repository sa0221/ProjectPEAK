# src/lora_communication/lora_receiver.py

import time
from SX127x.LoRa import *
from SX127x.board_config import BOARD
from .lora_config import configure_lora

BOARD.setup()
BOARD.reset()

class LoraReceiver(LoRa):
    """
    A class to handle LoRa message receiving.
    """

    def __init__(self, verbose=False):
        """
        Initialize the LoraReceiver.

        Args:
            verbose (bool): If True, print detailed information.
        """
        super(LoraReceiver, self).__init__(verbose)
        configure_lora(self)
        self.set_mode(MODE.RXCONT)
        self.set_dio_mapping([0, 0, 0, 0, 0, 0])  # DIO0 = 0 = rx_done

    def on_rx_done(self):
        """
        Callback function when a message is received.
        """
        BOARD.led_on()
        print("\nReceived:")
        self.clear_irq_flags(RxDone=1)
        payload = self.read_payload(nocheck=True)
        if payload:
            print("Payload:", payload)
        self.set_mode(MODE.RXCONT)
        BOARD.led_off()

def create_receiver():
    """
    Create and return a LoraReceiver object.

    Returns:
        LoraReceiver: A configured LoraReceiver object.
    """
    receiver = LoraReceiver(verbose=False)
    return receiver
