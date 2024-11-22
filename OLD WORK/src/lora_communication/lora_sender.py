# src/lora_communication/lora_sender.py

import sys
from time import sleep
from SX127x.LoRa import *
from SX127x.board_config import BOARD
from .lora_config import configure_lora

BOARD.setup()
BOARD.reset()

class LoraSender(LoRa):
    """
    A class to handle LoRa message sending.
    """

    def __init__(self, verbose=False):
        """
        Initialize the LoraSender.

        Args:
            verbose (bool): If True, print detailed information.
        """
        super(LoraSender, self).__init__(verbose)
        configure_lora(self)
        self.set_dio_mapping([1, 0, 0, 0, 0, 0])  # DIO0 = 1 = tx_done

    def on_tx_done(self):
        """
        Callback function when transmission is done.
        """
        print("\nTxDone")
        self.set_mode(MODE.STDBY)
        self.clear_irq_flags(TxDone=1)
        BOARD.led_off()

    def send_message(self, message):
        """
        Send a message using LoRa.

        Args:
            message (bytes): The message to send.
        """
        self.write_payload(list(message))
        BOARD.led_on()
        self.set_mode(MODE.TX)
        while not self.get_irq_flags()['tx_done']:
            sleep(0.1)
        self.on_tx_done()

def create_sender():
    """
    Create and return a LoraSender object.

    Returns:
        LoraSender: A configured LoraSender object.
    """
    sender = LoraSender(verbose=False)
    return sender
