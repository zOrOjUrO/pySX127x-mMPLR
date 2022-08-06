import hashlib
import collections
try:
    from collections import abc
    collections.MutableMapping = abc.MutableMapping
except:
    pass

from mMPLR import SecurePass

"""
    DestinationID   -       3 Bytes
    DeviceID        -       3 Bytes
    ServiceType     -       1 Byte
    SequenceNo      -       2 Bytes
    Flag            -       1 Byte
    Payload Size    -       3 Bytes
    BatchSize       -       2 Bytes
    * Batches       -       2 Bytes
    //BatchNo       -       2 Bytes
    Checksum        -       4 Bytes
    =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
            Header ==== 19 Bytes
    =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
    """

class mMPLR:

    def __init__(self, devId, password = '2bckr0w3', batchSize=10):
        self.DeviceID = str(devId)
        self.DestinationID = '1'
        self.PAYLD_SIZE = '0'
        self.ServiceType = '0' #0 - Text; 1 - Sensor; 2 - Image; 3- Audio, 4 - Control
        self.SequenceNo = '1'
        self.BatchSize = '1'
        self.Flag = '2' #0 - SYN;1 - SYN-ACK;2 - DATA;3 - BVACK;4 - FIN;5 - ACK; 6-RSND
        self.Checksum = b'\xd4\x1d\x8c\xd9\x8f\x00\xb2\x04\xe9\x80\t\x98\xec\xf8B~' #hashlib.md5(b'').digest()
        self.Payload = ''
        
        self.maxPayloadSize = 236 #255Bytes -19Bytes (Header)
        self.maxBatchSize = batchSize
        self.Batches = 1
        self.BACK = set()

        self.password = password
        

    def setDestinationID(self, deviceId):
        self.DestinationID = str(deviceId)
    
    def setPayloadSize(self, loadSize):
        self.PAYLD_SIZE = str(loadSize)

    def setServiceType(self, service): 
        if type(service) != str:
            self.ServiceType = str(service)
            return
        services = {"text":0, "sensor": 1, "image": 2, "audio": 3}
        self.ServiceType = str(services.get(service.lower(), 0))
        
    def setSequenceNo(self, seqNo):
        self.SequenceNo = str(seqNo)

    def setBatchSize(self, batchSize):
        assert self.maxBatchSize >= int(batchSize)
        self.BatchSize = str(batchSize)
    
    def getBatchSize(self):
        return int(self.BatchSize) 
    
    def setFlag(self, flag):
        if type(flag) != str:
            self.Flag = str(flag)
            return
        flags = {'SYN':0, 'SYN-ACK':1,'DATA':2,'BVACK':3,'FIN':4,'ACK':5}
        self.Flag = str(flags.get(flag.upper()))

    def genChecksum(self):
        header = bytes(self.DestinationID, 'utf-8').ljust(3)[:3]\
        +bytes(self.DeviceID, 'utf-8').ljust(3)[:3]\
        +bytes(self.ServiceType, 'utf-8').ljust(1)\
        +bytes(self.SequenceNo, 'utf-8').ljust(2)\
        +bytes(self.Flag, 'utf-8').ljust(1)\
        +bytes(self.PAYLD_SIZE, 'utf-8').ljust(3)\
        +bytes(self.BatchSize, 'utf-8').ljust(2)
        #+bytes(self.Batches, 'ascii').ljust(2))

        self.Checksum = hashlib.md5(header).digest()[:4] 
        return self.Checksum, header

    def setPayload(self, payload: str):
        assert(len(payload) <= self.maxPayloadSize)
        self.setPayloadSize(len(payload))
        self.Payload = payload

    def genHeader(self):
        checksum, head = self.genChecksum()
        return head+checksum[:16]

    def genPacket(self, packetNo, payload):
        #self.setFlag()
        self.setPayload(payload=payload)
        self.setSequenceNo(seqNo=packetNo)
        packet = self.genHeader() + bytes(self.Payload, 'utf-8')
        return packet

    def genFlagPacket(self, DestinationID, Service, BatchSize, Flag, Payload=""):
        self.setDestinationID(DestinationID)
        self.setServiceType(Service)
        self.setBatchSize(BatchSize)
        self.setFlag(flag=Flag)
        return self.genPacket(packetNo=0, payload=Payload)
        
    def getPackets(self, data, dataType, destinationId, encryptAgain=False):
        packets = []
        if encryptAgain: data = SecurePass.encrypt(data, self.password)
        leng = len(data)
        self.setDestinationID(destinationId)
        self.setBatchSize(leng//self.maxPayloadSize+ (1 if leng%self.maxPayloadSize else 0))
        self.setServiceType(dataType)
        i = 0
        while i < (leng//self.maxPayloadSize):
            packets.append(self.genPacket(i, data[i*self.maxPayloadSize: min((i+1)*self.maxPayloadSize, leng)])) 
            i += 1   
        if leng%self.maxPayloadSize != 0:
            packets.append(self.genPacket(i, data[i*self.maxPayloadSize: ]))        
        return packets

    def getPacketsAsBatches(self, data, dataType, destinationId, isEncrypted = False):
        maxBatchContentSize = self.maxBatchSize*self.maxPayloadSize
        if isEncrypted: data = SecurePass.encrypt(data, self.password)
        b = 0
        batches = []
        leng = len(data)
        while b < leng//maxBatchContentSize:
            batches.append(self.getPackets(data=data[b*maxBatchContentSize: min((b+1)*maxBatchContentSize, leng)], dataType=dataType, destinationId=destinationId, encryptAgain=False))
            b += 1
        if leng%maxBatchContentSize != 0:
            batches.append(self.getPackets(data=data[b*maxBatchContentSize: ], dataType=dataType, destinationId=destinationId, encryptAgain=False))
            b += 1
        self.Batches = b
        return batches

    def parsePacket(self, rawpacket):
        #print("Parsing Packet (length ", len(rawpacket), ") : ", rawpacket)
        assert len(rawpacket) >= 19
        rawheader = rawpacket[:19]
        header = {"DestinationUID":rawheader[:3].rstrip().decode('ascii'),
        "DeviceUID":rawheader[3:6].rstrip().decode('ascii'),
        "Service":int(rawheader[6:7].decode('ascii')),
        "SequenceNo":int(rawheader[7:9].decode('ascii')),
        "Flag":int(rawheader[9:10].decode('ascii')),
        "PayloadSize":int(rawheader[10:13].decode('ascii')),
        "BatchSize":int(rawheader[13:15].decode('ascii')),
        "Checksum":rawheader[15:] 
        }
        if header["Checksum"] != hashlib.md5(rawheader[:-4]).digest()[:4]:
            print("Packet Corrupt.\nPacket ",header["SequenceNo"], " to be resent")
            #self.BACK.append(header["SequenceNo"])
            return {"isCorrupt":True, "PacketNo":header["SequenceNo"]} 
        self.ackPacket(header["SequenceNo"])
        content = rawpacket[19:]  
        return {"Header": header, "Content": content}

    def parsePackets(self, packets, isRaw = True, isEncrypted = False):
        content = b''
        for pkt in packets:
            packet = self.parsePacket(pkt) if isRaw else pkt
            content += packet.get("Content", "")
        #reset BACK
        self.BACK = set()
        return content if not isEncrypted else bytes(SecurePass.decrypt(content, self.password), 'utf-8')

    def parsePacketsAsBatches(self, batches, isRaw = True, isEncrypted = False):
        content = b''
        for batch in batches:
            content += self.parsePackets(batch, isRaw=isRaw, isEncrypted=isEncrypted)
        return content

    def ackPacket(self, seqNo):
        try: self.BACK.remove(seqNo)
        except (KeyError, ValueError): pass

    def isBatchCorrupt(self):
        return True if len(self.BACK) else False

if __name__ == "__main__":
    mplr = mMPLR(devId='1')
    batches = mplr.getPacketsAsBatches("cz3gm8ix0gr092bnzyijsdmau4e8ublxb4gz2jx85gqir8r3sj5ekdigk139g6jalbe0xl1hro9xlvq2sewa8iqo9e46ap2eyu0coojtpfi6tzzre94719c17id9hpvhkw6amcvtmfdf1m9811o71xyx1yb3p9hx8hwcbo7f7qawlupgkm8kttbxqcbj0z53wotey1v33utg0lcjkbug4vx0jvunyxxfhbw0vjqaq493yyw5vsym6xcmkwy2z21ob9xgutg51n86nc9onrw8sgwp1v79bvl3pqo99bnlpsyorb4w1sct1cphr96qc7l6qi9v0u7dgvqiaq9w5ei9t3pvxqjux1dqhx23ffgdo1ke2ub9x4dpr2ioslyr8p2fyvwm30kpun5mok8deld43wmihc3c0ldg8yb01eu4xzdoc6fsmxsqs2poqa87ghdvxfqt24licn9hiureey069n3xdfsr7no8d21z5ndy45k1p6ndhxed",
                              1, 2)
    print("\n#Batches: ", mplr.Batches, "\n\n")
    print(*batches, sep="\n\n\n")
    # for packet in packets:
    #     l = [int(hex(e), 0) for e in packet]
    #     print(l, "\n", bytes(l), "\n\n")
    print(mplr.parsePacketsAsBatches(batches=batches))

    
        