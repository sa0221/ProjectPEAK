# src/lora_communication/lora_receiver.py

from time import sleep
from SX127x.LoRa import *
from SX127x.board_config import BOARD
from .lora_config import configure_lora

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

    def on_rx_done(self):
        """
        Callback function when a message is received.
        """
        print("\nReceived: ")
        payload = self.read_payload(nocheck=True)
        print(bytes(payload).decode("utf-8",'ignore'))
        self.set_mode(MODE.RXCONT)

def create_receiver():
    """
    Create and return a LoraReceiver object.

    Returns:
        LoraReceiver: A configured LoraReceiver object.
    """
    receiver = LoraReceiver(verbose=False)
    return receiver