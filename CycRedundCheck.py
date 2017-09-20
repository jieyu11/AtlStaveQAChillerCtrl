class ConvertCRC : 
  table = tuple()
  # crc16_Init() - Initialize the CRC-16 self.table (crc16_Table[])
  def __init__( self ):
      lst = []
      i = 0
      while( i < 256):
          data = (i << 1)
          crc = 0
          j = 8
          while( j > 0):
              data >>= 1
              if( (data ^ crc) & 0x0001):
                  crc = (crc >> 1) ^ 0xA001
              else:
                  crc >>= 1
              j -= 1
             
          lst.append( crc)
          # print "entry %d = %x" % ( i, self.table[i])
          i += 1
  
      self.table = tuple( lst)       
      return
  
  # given a Byte, Calc a modbus style CRC-16 by look-up self.table
  def calcByte(self, ch, crc):
      if( type(ch) == type("c")):
          by = ord( ch)
      else:
          by = ch
      crc = (crc >> 8) ^ self.table[(crc ^ by) & 0xFF]
      return (crc & 0xFFFF)
  
  def calcString(self, st, crc):
      # print "st = ", list( st)
      for ch in st:
          crc = (crc >> 8) ^ self.table[(crc ^ ord(ch)) & 0xFF]
          # print " crc=%x" % crc
      return crc
  
  def testCRC(self ):
  
      # test Modbus
      print ("testing Modbus messages with crc16.py")
      print ("test case #1:",)
      crc = 0xFFFF
      st = "\xEA\x03\x00\x00\x00\x64"
      for ch in st:
          crc = self.calcByte( ch, crc)
      if( crc != 0x3A53):
          print ("BAD - ERROR - FAILED!",)
          print ("expect:0x3A53 but saw 0x%x" % crc)
      else:
          print ("Ok")
         
      print ("test case #2:",)
      st = "\x4b\x03\x00\x2c\x00\x37"
      crc = self.calcString( st, 0xFFFF)
      if( crc != 0xbfcb):
          print ("BAD - ERROR - FAILED! ",)
          print ("expect:0xBFCB but saw 0x%x" % crc)
      else:
          print ("Ok")
         
      print ("test case #3:",)
      st = "\x0d\x01\x00\x62\x00\x33"
      crc = self.calcString( st, 0xFFFF)
      if( crc != 0x0ddd):
          print ("BAD - ERROR - FAILED!",)
          print ("expect:0x0DDD but saw 0x%x" % crc)
      else:
          print ("Ok")
  
      # test Modbus
      print
      print ("testing DF1 messages with crc16.py")
     
      print ("test case #1:",)
      st = "\x07\x11\x41\x00\x53\xB9\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
      crc = self.calcString( st, 0x0000)
      crc = self.calcByte( "\x03", crc)
      if( crc != 0x4C6B):
          print ("BAD - ERROR - FAILED!",)
          print ("expect:0x4C6B but saw 0x%x" % crc)
      else:
          print ("Ok")
      return
	 
if __name__ == '__main__':
    istCRCtool = ConvertCRC()
    istCRCtool.testCRC()

