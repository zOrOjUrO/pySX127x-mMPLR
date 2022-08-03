import base64
import os 

class B64Util():
    
    def __init__(self):
        self.Filepath = os.path.abspath("./Data/input.txt")
        self.B64String = b''
        self.Filetype = 0 #0 - Text, 1 - Sensor, 2 - Image, 3 - Audio, 4 - Control
        self.OutPath = os.path.abspath("./Data/output.txt")
    
    def encodeTo64(self):
        if self.Filepath == "":
            print("***No image Path Specified***")
        with open(self.Filepath, "rb") as f:
            self.B64String = base64.b64encode(f.read())

    
    def setOutputPath(self, path):
        self.OutPath = os.path.abspath(path)
    
    def setInputFile(self, filepath):
        self.Filepath = os.path.abspath(filepath)
        if (filepath.endswith(".flac") or filepath.endswith(".wav")): self.Filetype = 3
        elif (filepath.endswith(".jpg") or filepath.endswith(".jpeg") or filepath.endswith(".png")): self.Filetype = 2
        elif (filepath.endswith(".txt")): self.Filetype = 0
        else: 
            print("Invalid Input File Path") 
            return -1
        return 0

    def getB64String(self):
        self.encodeTo64()
        return self.B64String
    
    def setB64String(self, b64BytesString):
        self.B64String = b64BytesString
        return b64BytesString

    def writeToFile(self):
        if self.B64String == "":
            print("Nothing to Decode")
            return
        _64_decode = base64.b64decode(self.B64String) 
        with open(self.OutPath, 'wb') as _result: # create a writable image and write the decoded result
            _result.write(_64_decode)

if __name__ == "__main__":
    B64 = B64Util()
    #print(B64.setInputFile("filename"))
    print(B64.getB64String())
    print(B64.getB64String().decode('utf-8'))
    B64.writeToFile()

    B64.setInputFile("./Data/captured_img.jpg")
    B64.getB64String()
    B64.setOutputPath("./Data/output.jpg")
    B64.writeToFile()
