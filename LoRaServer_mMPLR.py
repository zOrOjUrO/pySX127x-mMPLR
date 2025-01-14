#!/usr/bin/env python3

""" This program asks a client for data and waits for the response, then sends an ACK. """

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

import time
from SX127x.LoRa import *
#from SX127x.LoRaArgumentParser import LoRaArgumentParser
from SX127x.board_config import BOARD

from mMPLR.mMPLR import mMPLR

#from mMPLR.base64Util import B64Util
BOARD.setup()
BOARD.reset()
#parser = LoRaArgumentParser("Lora tester")

"""
    State 0 - Connection Initiation State (SYN to be sent) 
    
    State 1 - SYN Acknowledged - Receive Connection Variables; Sending ACK

    State 2 - Connection Established; Receiving DATA

    State 3 - Batch Receive Complete; Sending BACK

    State 4 - Batch Partially Corrupted; Receiving Corrupt Packets

    State 5 - FIN Received :: Send FIN-ACK; Terminate Connection; Parse Message

"""

class mMPLRLoraServer(LoRa):
    def __init__(self, verbose=False):
        super(mMPLRLoraServer, self).__init__(verbose)
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([0] * 6)
        self.state=0                #0 - Listening; 1 - Connect Init; 2 - Connected; 3 - ACK Batch; 
                                    #4 - Receive Corrupt Batch; 5 - Connection Termination
        self.mplr    = mMPLR(devId=2, batchSize=1000)
        self.packets = list()

        self.currentDataType = 0    #0 - Text; 1 - Sensor; 2 - Image; 3- Audio, 4 - Control
        self.destId = '2'
        self.BatchSize = 0          #Number of packets being sent in the Current Batch
        self.brx_count = 0          #received packets in batch
        self.b_count = 0            #batch count

    def sendData(self, raw):
        data = [int(hex(c), 0) for c in raw]
        #print(data)
        self.write_payload(data)
        BOARD.led_on()
        self.set_mode(MODE.TX)
        time.sleep(3)

    def on_rx_done(self):
        BOARD.led_on()
        #print("\nRxDone")
        self.clear_irq_flags(RxDone=1)
        pkt = bytes(self.read_payload(nocheck=True)) # Receive Raw Packet
        BOARD.led_off()

        try: 
            packet = self.mplr.parsePacket(rawpacket=pkt)
            header = packet.get("Header")
            flag = header.get("Flag")
            seqNo = header.get("SequenceNo")

            if flag == 1:
                print("\nSYN-ACK Received")
                self.BatchSize = header.get("BatchSize")
                self.mplr.BACK = set(range(self.BatchSize))
                self.currentDataType = header.get("Service", 0)
                #parse the nBatches from packet body
                print("BatchSize: ",self.BatchSize,"\tDataType: ", self.currentDataType)
                #Send ACK
                time.sleep(1) # Wait for the client be ready
                self.state = 1                                              

            elif flag == 2 and self.state == 2:
                print("\nDATA Packet Received, Packet No",header.get("SequenceNo"))
                self.brx_count += 1
                self.packets.append(packet)
                time.sleep(2)
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT)

                if self.brx_count == self.BatchSize:
                    #send BVACK
                    time.sleep(1)
                    #b_count increment if batch not corrupt
                    self.state = 3

            elif flag == 2 and self.state == 3:
                #check for end of batches
                print("\nReceiving Batch", str(self.b_count+1),
                      "\nPacket of New Batch Received, Packet no",header.get("SequenceNo"))
                self.state = 2
                self.brx_count += 1
                self.BatchSize = header.get("BatchSize")
                self.mplr.BACK = set(range(self.BatchSize))
                self.packets.append(packet)
                self.mplr.ackPacket(seqNo)
                time.sleep(2)
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT)
                if self.brx_count == self.BatchSize:
                    #send BVACK
                    time.sleep(1)
                    self.state = 3
            
            elif flag == 2 and self.state == 4:
                print("\nReceiving Corrupt / Missing Batch Packet")
                if not packet.get("isCorrupt", False):
                    self.packets.insert(self.mplr.maxBatchSize * (self.b_count)+seqNo, packet)
                    self.mplr.ackPacket(seqNo)
                time.sleep(2)
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT)
                if not self.mplr.isBatchCorrupt():
                    #send BVACK
                    time.sleep(1)
                    self.state = 3

            elif flag == 4:
                print("\nReceived FIN")
                #send ACK
                self.state = 5

        except: 
            #Raw or Unstructured Packet Received 
            pass
        
        

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
        self.bretry_attempts = 0
        self.bcretry_attempts = 0          
        while True:
            while (self.state==0):
                self.packets.clear()
                input("Press Enter to Send SYN")
                
                syn = self.mplr.genFlagPacket(DestinationID=self.destId, Service=0, BatchSize=0, Flag=0)
                print ("Send: SYN")#, syn)
                print ("SYN Sent")
                self.sendData(syn)
                self.set_mode(MODE.SLEEP)
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT) #Receiver mode
                time.sleep(1) 
                
                start_time = time.time()
                while (time.time() - start_time < 10): # wait until receive data or 60s
                    pass;
            
            while (self.state == 1):
                print ("Send: ACK")
                ack = self.mplr.genFlagPacket(DestinationID=self.destId, Service=self.currentDataType, BatchSize=self.BatchSize, Flag=5)
                self.sendData(ack)
                self.set_mode(MODE.SLEEP)
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT)
                time.sleep(2)
                self.state = 2 
                
            while (self.state == 2):
                print ("Connected. Waiting For DATA")
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT) # Receiver mode
                start_time = time.time()
                while (time.time() - start_time < 30): # wait until receive data or 20s
                    pass;
                self.state = 3
                #TODO: Implement Fallback for Timeout (BACK)
                

            while (self.state == 3):
                self.brx_count = 0
                self.b_count += 1
                print("Sending Batch ACK")
                bvack = self.mplr.genFlagPacket(DestinationID=self.destId, Service=self.currentDataType, BatchSize=self.BatchSize, 
                                                Flag=3, Payload=','.join(map(str, self.mplr.BACK)))
                self.state = 4 if self.mplr.isBatchCorrupt() else 3
                self.sendData(bvack)
                self.set_mode(MODE.SLEEP)
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT)
                time.sleep(2)
                #self.state = 2 
                start_time = time.time()
                while (time.time() - start_time < 15): # wait until receive data or 15s
                    pass;
                #TODO: Implement Fallback for Timeout (Terminate after 3 Attempts) 

            #state 4 -> Corrupt Packet found in the Batch, Receive and replace packets 
            while (self.state == 4):
                print("Waiting for Corrupt / Missing Packets of the Previous Batch")
                self.set_mode(MODE.SLEEP)
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT)
                time.sleep(2)
                start_time = time.time()
                while (time.time() - start_time < 10): # wait until receive data or 10s
                    pass;
                #TODO: Implement Fallback for Timeout (Terminate after 3 Attempts)

            while (self.state == 5):
                #Should do 4 way?
                print("\nSend FIN-ACK")
                ack = self.mplr.genFlagPacket(DestinationID=self.destId, Service=self.currentDataType, BatchSize=self.BatchSize, Flag=5)
                self.sendData(ack)
                self.set_mode(MODE.SLEEP)
                print("\nConnection Terminated")
                self.state = 0
                #parse the content
                receivedContent = self.mplr.parsePackets(self.packets, isRaw=False, isEncrypted = True)
                print("Received Content: ", receivedContent.decode())
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT)
                time.sleep(1)

            
            

            if(self.state == 3): 
                #Fallback for Timeout (Terminate)  
                self.bretry_attempts += 1
                if self.bretry_attempts == 3:
                    print("\n\nNo Response.\nDisconnected\n")
                    self.state = 0
                    self.bretry_attempts = 0
            
            if(self.state == 4): 
                #Fallback for Timeout (Terminate)  
                self.bcretry_attempts += 1
                if self.bcretry_attempts == 3:
                    print("\n\nNo Response.\nDisconnected\n")
                    self.state = 0

            self.reset_ptr_rx()
            self.set_mode(MODE.RXCONT) # Receiver mode
            time.sleep(10)


lora = mMPLRLoraServer(verbose=False)
#args = parser.parse_args(lora) # configs in LoRaArgumentParser.py

#     Slow+long range  Bw = 125 kHz, Cr = 4/8, Sf = 4096chips/symbol, CRC on. 13 dBm
lora.set_pa_config(pa_select=1, max_power=21, output_power=15)
lora.set_bw(BW.BW125)
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
