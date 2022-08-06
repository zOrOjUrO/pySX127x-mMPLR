#!/usr/bin/env python3

""" This program sends a response whenever it receives the "CNT" """

# Copyright 2022 zOrOjUrO.
#
# This file is part of pySX127x-mMPLR, a fork of rpsreal/pySX127xw which is fork of mayeranalytics/pySX127x.
#
# pySX127x is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# pySX127x is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You can be released from the requirements of the license by obtaining a commercial license. Such a license is
# mandatory as soon as you develop commercial activities involving pySX127x without disclosing the source code of your
# own applications, or shipping pySX127x with a closed source product.
#
# You should have received a copy of the GNU General Public License along with pySX127.  If not, see
# <http://www.gnu.org/licenses/>.
import string
import random

import time
from SX127x.LoRa import *
#from SX127x.LoRaArgumentParser import LoRaArgumentParser
from SX127x.board_config import BOARD

from mMPLR.mMPLR import mMPLR

BOARD.setup()
BOARD.reset()
#parser = LoRaArgumentParser("Lora tester")


class mMPLRLoraClient(LoRa):
    def __init__(self, verbose=False):
        super(mMPLRLoraClient, self).__init__(verbose)
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([0] * 6)
        self.state = 0
        self.mplr = mMPLR(devId=1,batchSize=10)
        self.currentBatch = 0
        self.resendingBatch = []
        self.corrupt = []
        self.nBatches = 0

    def sendData(self, raw):
        data = [int(hex(c), 0) for c in raw]
        print("\nSending : ")#,bytes(data))
        self.write_payload(data)
        BOARD.led_on()
        self.set_mode(MODE.TX)
        time.sleep(3)

    def on_rx_done(self):
        BOARD.led_on()
        #print("\nRxDone")
        self.clear_irq_flags(RxDone=1)
        p = self.read_payload(nocheck=True)
        #print(p)
        pkt = bytes(p)
        #print(packet) # Receive DATA
        BOARD.led_off()

        packet = self.mplr.parsePacket(rawpacket=pkt)
        header = packet.get("Header")
        flag = header.get("Flag")
        if flag == 0:
            print("\nSYN Received")
            self.destId = header.get("DeviceUID")
            #Generate Data for Transmission
            with open('img.txt') as f:
                imgData = f.readlines()
            res = ''.join(random.choices(string.ascii_letters, k=2600))
            self.batches = self.mplr.getPacketsAsBatches(data = imgData[0]
                                                ,dataType="2", 
                                                destinationId=self.destId,
                                                isEncrypted=True)
            #print("Generated: ", *self.batches, sep="\n")
            
            time.sleep(3) # Wait for the client be ready            
            self.state = 1
            
        
        elif flag==5:
            print("\nReceived ACK")
            time.sleep(3)
            if self.state == 1:
                self.state = 2
                #sending data
                print("\nSending ", str(self.mplr.Batches), " Batches of Packets.\n\n" )

            elif self.state == 5:
                print("\nFIN-ACK received")
                print("Send: ACK")
                ack = self.mplr.genFlagPacket(DestinationID=self.destId, Service=0, BatchSize=self.mplr.BatchSize, Flag=5)
                self.sendData(ack)
                self.set_mode(MODE.SLEEP)
                print("\nConnnection Terminated")
                self.state = 0
                time.sleep(2)
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT)
                print("\n\n\Listening for new Connections . . .\n\n")
        
        elif flag==3 and self.state == 3:
            print("Batch ACK received")
            payloadSize = header.get("PayloadSize")
            payload = packet.get("Content")
            if payloadSize == 0:
                #implement moving to next here or in state 2
                self.currentBatch += 1
                if self.currentBatch > len(self.batches)-1:
                    self.state = 4
                else:
                    self.state = 2
            else:
                self.resendingBatch = list(map(int, bytes(payload).decode("utf-8").split(",")))
                self.state = 6
            
            
        elif flag == 4:
            self.state = 4
        
            
        else:
            time.sleep(5)
            self.reset_ptr_rx()
            self.set_mode(MODE.RXCONT)

    def on_tx_done(self):
        print("\nTxDone")
        print(self.get_irq_flags())

    def on_cad_done(self):
        print("\non_CadDone")
        print(self.get_irq_flags())

    def on_rx_timeout(self):
        print("\non_RxTimeout")
        print(self.get_irq_flags())

    def on_valid_header(self):
        print("\non_ValidHeader")
        print(self.get_irq_flags())

    def on_payload_crc_error(self):
        print("\non_PayloadCrcError")
        print(self.get_irq_flags())

    def on_fhss_change_channel(self):
        print("\non_FhssChangeChannel")
        print(self.get_irq_flags())

    def start(self):
        print("\nClient Initialized\n")
                
        while True:
            self.reset_ptr_rx()
            self.set_mode(MODE.RXCONT) # Receiver mode
            while self.state == 0:
                pass;
            
            while self.state == 1: #state after receiving syn
                initBatchSize = self.mplr.getBatchSize() if self.mplr.Batches == 1 else self.mplr.maxBatchSize
                synack = self.mplr.genFlagPacket(DestinationID=self.destId,
                                            Service=0,
                                            BatchSize=initBatchSize,
                                            Flag=1,
                                            Payload="#Batches:"+str(self.mplr.Batches))
                print ("Send: SYN-ACK")
                self.sendData(synack)
                self.set_mode(MODE.SLEEP)
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT)
                time.sleep(2)
                start_time = time.time()
                while (time.time()-start_time < 10):
                    pass;
                
            while self.state == 2: #packets/batches sending state
                time.sleep(3)
                for seq, packet in enumerate(self.batches[self.currentBatch]):
                    
                    """
                    count += 1
                    if count == 3 and self.currentBatch == 0:
                        print(packet)
                        print("skipped 3rd")
                        continue
                    """
                    print("\nSend: DATA ", str(self.currentBatch), ".",str(seq))
                    ##print(packet)
                    self.sendData(packet)
                    self.set_mode(MODE.TX)
                    time.sleep(3)             
                self.set_mode(MODE.SLEEP)
                self.state = 3
                
                
            while self.state == 3: #waiting for batchAck
                print("waiting for batchAck")
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT) #wait for batch ack
                time.sleep(1)                
                start_time = time.time()
                while (time.time() - start_time < 10): # wait until receive batch ack or 10s
                    pass;
                
                #self.state = 4 #temporary setup to go to state 4
                #pass;
            
            while self.state == 4: #FIN sending state should be done when all batches are sent
                self.currentBatch = 0
                self.batches.clear()
                fin = self.mplr.genFlagPacket(DestinationID=self.destId,
                                                Service=0,
                                                BatchSize=self.mplr.BatchSize,
                                                Flag=4)
                print("Sending FIN")
                self.sendData(fin)
                self.state = 5
                self.set_mode(MODE.SLEEP)
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT)
                time.sleep(2)
                start_time = time.time()
                while (time.time() - start_time < 10): # wait until receive batch ack or 10s
                    pass;
            
            while self.state == 6:
                for idx in self.resendingBatch:
                    self.sendData(self.batches[self.currentBatch][idx])
                    self.set_mode(MODE.TX)
                    time.sleep(5)             
                self.set_mode(MODE.SLEEP)
                self.state = 3 #BatchAck state
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT) #wait for batch ack
                time.sleep(1)
                
                start_time = time.time()
                while (time.time() - start_time < 10): # wait until receive batch ack or 10s
                    pass;
                    
                
                
                
            

lora = mMPLRLoraClient(verbose=False)
#args = parser.parse_args(lora) # configs in LoRaArgumentParser.py

#     Slow+long range  Bw = 125 kHz, Cr = 4/8, Sf = 4096chips/symbol, CRC on. 13 dBm
lora.set_pa_config(pa_select=1, max_power=21, output_power=15)
lora.set_bw(BW.BW125)
#lora.set_coding_rate(CODING_RATE.CR4_8) 
#lora.set_spreading_factor(12)
lora.set_coding_rate(CODING_RATE.CR4_5)
lora.set_spreading_factor(7)
lora.set_rx_crc(True)
#lora.set_lna_gain(GAIN.G1)
#lora.set_implicit_header_mode(False)
lora.set_low_data_rate_optim(True)

#  Medium Range  Defaults after init are 434.0MHz, Bw = 125 kHz, Cr = 4/5, Sf = 128chips/symbol, CRC on 13 dBm
#lora.set_pa_config(pa_select=1)



assert(lora.get_agc_auto_on() == 1)

try:
    print("START")
    lora.start()
except KeyboardInterrupt:
    sys.stdout.flush()
    print("Exit")
    sys.stderr.write("KeyboardInterrupt\n")
finally:
    sys.stdout.flush()
    print("Exit")
    lora.set_mode(MODE.SLEEP)
BOARD.teardown()


