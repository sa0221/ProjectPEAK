# src/lora_communication/lora_sender.py

from time import sleep
from SX127x.LoRa import *
from SX127x.board_config import BOARD
from .lora_config import configure_lora

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

    def on_tx_done(self):
        """
        Callback function when transmission is done.
        """
        print("\nTxDone")
        self.set_mode(MODE.STDBY)
        self.clear_irq_flags(TxDone=1)

    def send_message(self, message):
        """
        Send a message using LoRa.

        Args:
            message (str): The message to send.
        """
        self.write_payload(list(message.encode()))
        self.set_mode(MODE.TX)
        while (self.get_irq_flags()['tx_done'] == 0):
            sleep(0.1)
        self.clear_irq_flags(TxDone=1)

def create_sender():
    """
    Create and return a LoraSender object.

    Returns:
        LoraSender: A configured LoraSender object.
    """
    sender = LoraSender(verbose=False)
    return sender