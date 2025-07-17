# Simple byte buffer for MD
#@author La Tryphe
#@category _NEW_
#@keybinding 
#@menupath 
#@toolbar 


#TODO Add User Code Here

import os

class Buffer:
	def __init__(self, length = 65536):
		self.length = length
		self.data = bytearray([0] * length)
		self.pos = 0
		self.subpos = 7
		self.max_indice = 0
		self.stack = []
	
	def push(self):
		self.stack.append((self.pos, self.subpos))

	def pop(self):
		self.pos, self.subpos = self.stack.pop()

	def __len__(self):
		return self.max_indice + 1

	def align(self, n=2):
		if self.pos % n:
			self.pos += (n - self.pos % n)
			
	def set_pos(self, pos):
		self.pos = pos
		self.subpos = 7
		self.max_indice = max(self.max_indice, pos)
	
	def advance_by(self, d):
		self.set_pos(self.pos + d)
	
	def __getitem__(self, pos):
		self.max_indice = max(self.max_indice, pos)
		return self.data[pos]
	
	def __setitem__(self, pos, val):
		self.max_indice = max(self.max_indice, pos)
		self.data[pos] = val
	
	def write_b(self, val, pos = None):
		val &= 0xFF
		if pos is None:
			self[self.pos] = val
			self.pos += 1
		else:
			self[pos] = val
	
	def write_nibble(self, val):
		if self.subpos == 7:
			self[self.pos] = (self[self.pos] & 0x0F) + (val << 4)
			self.subpos = 3
		else:
			self[self.pos] = (self[self.pos] & 0xF0) + val
			self.subpos = 7
			self.pos += 1
	
	def write_w(self, val, pos = None):
		if pos is None:
			self.write_b(val >> 8)
			self.write_b(val & 0xFF)
		else:
			self.write_b(val >> 8, pos)
			self.write_b(val & 0xFF, pos + 1)
			
	def write_l(self, val, pos = None):
		if pos is None:
			self.write_b(val >> 24)
			self.write_b((val >> 16) & 0xFF)
			self.write_b((val >> 8) & 0xFF)
			self.write_b(val & 0xFF)
		else:
			self.write_b(val >> 24, pos)
			self.write_b((val >> 16) & 0xFF, pos + 1)
			self.write_b((val >> 8) & 0xFF, pos + 2)
			self.write_b(val & 0xFF, pos + 3)
	
	def write(self, other, pos=None):
		if isinstance(other, list):
			for x in other:
				self.write_b(x)
		elif isinstance(other, Buffer):
			self.write_buffer(other, pos)
		elif isinstance(other, str):
			self.write_string(other, pos)
		else:
			raise Exception()
	
	def set_size(self, n):
		if n < len(self.data):
			self.data = self.data[:n]
		elif n > len(self.data):
			self.data += bytearray([0] * (n - len(self.data)))
		self.max_indice = n - 1
			
	def write_buffer(self, other, pos=None):
		if pos is None:
			pos_ = self.pos
		else:
			pos_ = pos
#		print(type(self.data), type(other.data))
		
		self.data[pos_:pos_ + len(other)] = other.data
		self.max_indice = max(self.max_indice, pos_ + len(other))
		if pos is None:
			self.pos = pos_ + len(other)

	def write_string(self, s, pos=None):
		if pos is None:
			pos_ = self.pos
		else:
			pos_ = pos
		s = s.replace(' ', '')
		for i in range(0, len(s), 2):
			self.write_b(int(s[i:i+2], 16), pos_)
			pos_ += 1
			
		self.max_indice = max(self.max_indice, pos_)
		if pos is None:
			self.pos = pos_
	
	def write_text(self, s, pos=None, encoding=None):
		if pos is None:
			pos_ = self.pos
		else:
			pos_ = pos
		for c in s:
			if encoding:
				c_ = encoding.index(c)
			else:
				c_ = ord(c)
			self.write_b(c_, pos_)
			pos_ += 1
		if pos is None:
			self.pos = pos_
			
	def read_bit(self):
		val = (self[self.pos] >> self.subpos) & 1
		self.subpos -= 1
		if self.subpos < 0:
			self.pos += 1
			self.subpos = 7
#		print("read bit %s" % val)
		return val
	
	def read_bits(self, n):
		val = 0
		for _ in range(n):
			val = 2*val + self.read_bit()
		return val
	
	def read_b(self, pos = None, signed = False):
		if pos is None:
			val = self[self.pos]
			self.pos += 1
		else:
			val = self[pos]
		if signed and val >= 0x80:
			val -= 0x100
		return val

	def read_w(self, pos = None, signed = False):
		if pos is None:
			val = (self[self.pos] << 8) + self[self.pos + 1]
			self.pos += 2
		else:
			val = (self[pos] << 8) + self[pos + 1]
		if signed and val >= 0x8000:
			val -= 0x10000
		return val

	def read_l(self, pos = None, signed = False):
		if pos is None:
			val = (self[self.pos] << 24) + (self[self.pos + 1] << 16) + (self[self.pos + 2] << 8) + self[self.pos + 3]
			self.pos += 4
		else:
			val = (self[pos] << 24) + (self[pos + 1] << 16) + (self[pos + 2] << 8) + self[pos + 3]
		if signed and val >= 0x80000000:
			val -= 0x100000000
		return val

	def read_pattern(self, surf, pos):
		x0, y = pos
		for j in range(8):
			x = x0
			data = self.read_l()
			for i in range(8):
				surf.set_at(x, y, (data >> 28) & 15)
				x += 1
				data = (data << 4) & 0xFFFFFFFF
			y += 1
	
	def dump(self):
		print("dump")
		for k in range(0, self.max_indice, 16):
			row = "0x%04X: " % k
			row += " ".join(["%02X" % val for val in self.data[k : k + 16]])
			print(row)
			
	def save(self, path):
		with open(path, 'wb') as f:
			f.write(self.data[:self.max_indice+1])
	
	@staticmethod
	def load(path):
		with open(path, 'rb') as f:
			data = f.read()
		
		buf = Buffer(length = len(data))
		buf.data = bytearray(data)
		buf.max_indice = len(data) - 1
		return buf
	
	def write_s68(self, path):
		def write_code(code, addr):
			print("%X" % addr)
			self.set_pos(addr)
			for k in range(0, len(code), 2):
				self.write_b(int(code[k : k + 2], 16))

		with open(path) as f:
			lines = f.readlines()
		
		for line in lines:
			if line.startswith("S1"):
				addr = int(line[4:8], 16)
				code = line.strip()[8:-2]
				write_code(code, addr)

			elif line.startswith("S2"):
				addr = int(line[4:10], 16)
				code = line.strip()[10:-2]
				write_code(code, addr)
			
	def include(self, path, symbols={}, show_symbols=1):

		if show_symbols & 1:
			print("\tSymbols table:")
			for s in symbols:
				print("\t\t%s:\t0x%X" % (s, symbols[s]))

		res = ["%s equ %s\n" % (k, symbols[k]) for k in symbols]
		
		with open(path) as f:
			res = res + f.readlines()
		
		with open("__temp__.asm", 'w') as f:
			f.write(''.join(res))
	
		os.system("bin\\asm68k.exe /ps __temp__.asm,__temp__.s,__temp__.sym")
		
		with open("__temp__.s") as f:
			lines = f.readlines()
		
		for line in lines:
			line = line.strip()
			if line.startswith("S"):
				line_type = line[1]
				if line_type == "3":
					line_ln = int(line[2:4], 16)
					line_addr = int(line[4:12], 16)
					line_data = line[12:4+2*line_ln-2]
					if show_symbols & 2:
						print("%X: %s" % (line_addr, line_data))
					self.write(line_data, line_addr)
					

if __name__ == "__main__":
	buf = Buffer.get_program()
	buf.save('out.md')

   