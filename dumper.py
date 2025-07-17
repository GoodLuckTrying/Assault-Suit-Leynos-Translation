# -*- coding: utf-8 -*-


from buffer import Buffer
import numpy as np
import png

class Context:
	pass



def draw_ptrn(dest, x, y, attrs, verbose=False):
	priority = (attrs & 0x8000) != 0
	pal = (attrs >> 13) & 3
	vflip = (attrs & 0x1000) != 0
	hflip = (attrs & 0x0800) != 0
	tid = attrs & 0x7ff
	
	if patterns[tid] is None:
		if verbose:
			print("warning: no ptrn #%x" % tid)
	else:
		if verbose:
			print("drawing pattern #%03x at (%d, %d)" % (tid, x, y))
		tile = patterns[tid].copy()
		if vflip:
			tile = tile[::-1,:]
		if hflip:
			tile = tile[:,::-1]
		dest_ = dest[y:y+8, x:x+8]
		mask = (tile & 15) != 0
		dest_[mask] = priority*64 + pal*16 + tile[mask]

def load_tile(buf):
#	print("load_tile from %x" % buf.pos)
	tile = np.zeros((8, 8), dtype=np.uint8)
	x = y = 0
#	row = ""
	for _ in range(32):
		v = buf.read_b()
		tile[y, x] = v >> 4
#		row += "%x" % (v >> 4)
		tile[y, x + 1] = v & 15
#		row += "%x" % (v & 15)
		x += 2
		if x == 8:
#			print("\t%s" % row)
#			row = ""
			x = 0
			y += 1
	return tile

def save_png8(surf, palette, path):
	height, width = surf.shape
	w = png.Writer(width, height, palette=palette, bitdepth=8)
	with open(path, 'wb') as f:
		w.write(f, surf)

palette = [
	(0, 0, 0), (253, 253, 253), (0, 253, 0), (0, 253, 253), (253, 0, 0), (253, 0, 253), (253, 253, 0), (253, 253, 253), 
	(126, 126, 126), (0, 0, 126), (0, 126, 0), (0, 126, 126), (126, 0, 0), (126, 0, 126), (126, 126, 0), (191, 191, 191)
]*8

patterns = [None]*0x800

def clear_patterns():
	for i in range(0x800):
		patterns[i] = None

def save_vram(path, palette):
	width = 16
	height = 0x80
	surf = np.zeros((8*height, 8*width), dtype=np.uint8)

	i = 0
	for y in range(height):
		for x in range(width):
			draw_ptrn(surf, x*8, y*8, i)
			i += 1

	save_png8(surf, palette, path)

def md_to_rgb(x):
	r, g, b = (x & 15), ((x >> 4) & 15), ((x >> 8) & 15)
	r, g, b = r*255//14, g*255//14, b*255//14
	
#	print("%03X -> (%d, %d, %d)" % (x, r, g, b))
	return (r, g, b)

def load_palette(col_id, sz, transparency=True):
	for i in range(sz):
		palette[col_id] = palette[col_id + 64] = md_to_rgb(source.read_w())
		if transparency and (col_id & 15 == 0):
			palette[col_id] = palette[col_id + 64] = md_to_rgb(0xe0e)
		col_id += 1


def load_ptrns_bank(src, bank_id):
	res = Buffer()
	
	# 8b2c
	next_data = 1
	written_bytes = 0
	left_nibble = False
	
	start = src.read_l(0x3d800 + 4*bank_id)
	print("patterns at 0x%x" % start)
	src.set_pos(start)
	
	nb_tiles = src.read_b()
	is_compressed = src.read_b()
	if is_compressed:
		# 8b56
		if nb_tiles == 0:
			nb_tiles = 256
		
		nb_bytes = nb_tiles * 32
		
		last_val = -1

		while written_bytes < nb_bytes:
			# 8b64
			left_nibble = not left_nibble
			if left_nibble:
				val = src.read_b(pos=src.pos) >> 4
			else:
				val = src.read_b() & 0xf

			if val == last_val:
				# 8b7c
				left_nibble = not left_nibble
				if left_nibble:
					cnt = src.read_b(pos=src.pos) >> 4
				else:
					cnt = src.read_b() & 0xf
				
				for _ in range(cnt + 1):
					next_data = (next_data << 4) + val
					if next_data >= 0x10000:
						res.write_w(next_data)
						written_bytes += 2
						next_data = 1
				last_val = val
				
			else:
				# 8ba8
				last_val = val
				next_data = (next_data << 4) + val
				if next_data >= 0x10000:
					res.write_w(next_data)
					written_bytes += 2
					next_data = 1
			# 8bba: end loop

	else:
		# 8bc0
		for _ in range(nb_tiles + 1):
			for _ in range(8):
				res.write_l(src.read_l())

	return res

def load_ptrns(res, t_id, nb_ptrns):
	print("load_ptrns(t_id=%x, nb_ptrns=%x)" % (t_id, nb_ptrns))
	for _ in range(nb_ptrns):
		tile = load_tile(res)
		patterns[t_id] = tile
		t_id += 1

def decompress_tilemap(buf, base_ptrn, pal_id=0):
	type_ = buf.read_b()
	print(type_)
	if type_ == 2:
		width = buf.read_b()
		height = buf.read_b()
		pal_flags = pal_id << 13
		flip_flags = 0
		
#		res = np.zeros((height*8, width*8), dtype=np.uint8)
		res = np.zeros((height*8, width*8), dtype=np.uint8)
		print(res.shape)
		x = y = 0
		
		while True:
			c = buf.read_b()
			
			if c == 0xff:
				break
			
			elif c == 0xfe:
				counter = buf.read_b()
				c = buf.read_b()
				for _ in range(counter):
					draw_ptrn(res, x, y, (c + base_ptrn) | flip_flags | pal_flags, verbose=True)
					y += 8
					if y >= height*8:
						y = 0
						x += 8
					

			elif c == 0xfd:
				flip_flags = 0
			
			elif c == 0xfc:
				flip_flags = 0x800
			
			elif c == 0xfb:
				flip_flags = 0x1000
			
			elif c == 0xfa:
				flip_flags = 0x1800
			
			
			else:
				draw_ptrn(res, x, y, (c + base_ptrn) | flip_flags | pal_flags, verbose=True)
				y += 8
				if y >= height*8:
					y = 0
					x += 8
	
	return res

def compute_pos(d1, d2, d3, below=True):
	d0 = d2*128 + d1*2 + d3
	if below:
		d0 = d0*0x10001 + 0x80
	return d0

def fun_12162(buf, d1, d2, d3, d4, d5):
	res = Buffer()
	
	d6 = buf.read_b(buf.pos + 1)
	d7 = buf.read_b(buf.pos + 2)
	
	if buf.read_b(buf.pos) == 1:
		# 12178
		dat_b796 = 2
		dat_b798 = 6 + 2*d6
		height = dat_b78e = d6 - 1
		# goto #121c2
		
	else:
		#1219e
		dat_b796 = 6 + 2*d6
		dat_b798 = 2
		height = dat_b78e = d7 - 1

	# 121c2
	buf.pos += 3
	d1 = compute_pos(d1, d2, d3, below=False)
	pal_flags = d5 << 13
	
	# getEndOfVdpQueue
	# res.push()
	a1 = a2 = res.pos
	dat_b7a0 = 6
	
	d0 = d6*2
	d5 = d7 - 1
	
	# 121f2
	for _ in range(d5 + 1):
		res.write_w(0xfffd)
		res.write_w(d1)
		res.write_w(d6)
		
		d1 += 0x80
		res.pos += d0
		
	# 12204
	# setEndOfVdpQueue
	# res.pop()

	flip_flags = 0
	counter = 0
	res.pos = dat_b7a0

	while True:
		# @next2
		d2 = buf.read_b(pos = buf.pos)
		print("read %02x" % d2)
		if d2 == 0xff:
			# code_ff
			print("code ff")
			return res
	
		elif d2 == 0xfd:
			# code_fd
			flip_flags = 0
			print("code fd: flip_flags=%x" % flip_flags)
			# goto continue2_1
		elif d2 == 0xfc:
			# code_fc
			flip_flags = 0x800
			print("code fc: flip_flags=%x" % flip_flags)
			# goto continue2_1
		elif d2 == 0xfb:
			# code_fb
			flip_flags = 0x1000
			print("code fb: flip_flags=%x" % flip_flags)
			# goto continue2_1
		elif d2 == 0xfa:
			# code_fa
			flip_flags = 0x1800
			print("code fa: flip_flags=%x" % flip_flags)
		elif d2 > 0xf9:
			# not_fa
			counter = buf.read_b(pos=buf.pos + 1)
			print("code not fa: counter=%d" % counter)
			counter -= 1
			buf.pos += 2
			continue
			# goto @next2
		else:
			print("write %02x at 0x%x (0x%x)" % ((d2 + d4) | flip_flags | pal_flags, res.pos, res.pos + 0xff8118))
			res.write_w((d2 + d4) | flip_flags | pal_flags, pos=res.pos)
			res.pos += dat_b796
			if height != 0:
				height -= 1
				# goto continue2_1
			else:
				height = dat_b78e
				res.pos = dat_b7a0 + dat_b798
				dat_b7a0 = res.pos

		# continue2_1
		d6 = 1
		# continue2_2
		if counter == 0:
			# 122ea
			buf.pos += d6
		else:
			# 122f0
			counter -= 1


def get_pos(val):
	val &= 0x1fff
	y = val // 128
	x = val % 128

	return 8*x//2, 8*y

def build_tilemap(buf, width, height):
	# 11762
	
	buf.set_pos(0)
	res = np.zeros((height*8, width*8), dtype=np.uint8)
	tilemap = np.zeros((height, width), dtype=np.uint16())
	tilemap[:, :] = 0xffff
	
	while buf.pos < len(buf):
		# 1176c
		d1 = buf.read_w()
		if d1 == 0xffff:
			# 1178e
			vpos = buf.read_w()
			nb_bytes = buf.read_w()
			print("code 0xffff: read 0x%x bytes from vpos %04x" % (vpos, nb_bytes))
			# goto 11a3a
			
		elif d1 == 0xfffe:
			# 117ae
			vpos = buf.read_w()
			x, y = get_pos(vpos)
			nb_bytes = buf.read_w()
			print("code 0xfffe: write 0x%x bytes to vpos %04x" % (nb_bytes, vpos))
			for _ in range(nb_bytes):
				tid = buf.read_w()
				draw_ptrn(res, x, y, tid, verbose=True)
				tilemap[y//8, x//8] = tid
				x += 8
			# goto 11a3a
			
		elif d1 == 0xfffd:
			# 117ce
			vpos = buf.read_w()
			x, y = get_pos(vpos)
			nb_bytes = buf.read_w()
			print("code 0xfffd: DMA write 0x%x bytes to vpos %04x" % (nb_bytes, vpos))
			for _ in range(nb_bytes):
				tid = buf.read_w()
				if 0 <= x < width*8 and 0 <= y < height*8:
					draw_ptrn(res, x, y, tid, verbose=True)				
					tilemap[y//8, x//8] = tid
				else:
					print("pattern %x ignored at (%d, %d)" % (tid, x, y))
				x += 8
			# goto 11a3a

		elif d1 == 0xfffc:
			# 11868
			src_vpos = buf.read_w()
			x, y = get_pos(src_vpos)
			nb_bytes = buf.read_w()
			src_data = buf.read_l()
			
			print("code 0xfffc: write 0x%x bytes from ROM 0x%x to vpos %04x" % (nb_bytes, src_data, vpos))
			source.set_pos(src_data)
			for _ in range(nb_bytes):
				tid = source.read_w()
				draw_ptrn(res, x, y, tid, verbose=True)				
				tilemap[y//8, x//8] = tid
				x += 8
			# goto 11a3a
		
		elif d1 == 0xfffb:
			# 1188a
			vpos = buf.read_w()
			x, y = get_pos(src_vpos)
			nb_bytes = buf.read_w()
			src_data = buf.read_l()
			
			print("code 0xfffb: DMA write 0x%x bytes from ROM 0x%x to vpos %04x" % (nb_bytes, src_data, vpos))
			source.set_pos(src_data)
			for _ in range(nb_bytes):
				tid = source.read_w()
				draw_ptrn(res, x, y, tid, verbose=True)				
				tilemap[y//8, x//8] = tid
				x += 8
			# goto 11a3a
		
		elif d1 == 0xfffa:
			src_vpos = buf.read_w()
			x, y = get_pos(src_vpos)
			nb_bytes = buf.read_w()
			src_data = buf.read_w()
			autostep = buf.read_w()
			
			print("code 0xfffa: vpos=%x x=%d y=%d nb_bytes=%x src_data=%x autostep=%d" % (vpos, x, y, nb_bytes, src_data, autostep))
			# goto 11a3a
		
		elif d1 == 0xfff9:
			# 1199c 
			print("code 0xfff9: write %04x to VDP control port" % buf.read_w())
			# goto 11a3a
			
		elif d1 == 0xfff8:
			# 119a6 
			print("code 0xfff8: write %04x to VDP data port" % buf.read_w())
			# goto 11a3a
		
		elif d1 == 0xfff7:
			src_vpos = buf.read_w()
			x, y = get_pos(src_vpos)
			nb_bytes = buf.read_w()
			src_data = buf.read_w()
			autostep = buf.read_w()
			
			print("code 0xfff7: vpos=%x x=%d y=%d nb_bytes=%x src_data=%x autostep=%d" % (src_vpos, x, y, nb_bytes, src_data, autostep))
			# goto 11a3a
			
		else:
			# 11a30
			print("code 0xfff8: write %04x to VDP data port" % buf.read_w())
			# goto 11a3a
		
		# 11a3a
		
	# 11a3e
	for row in tilemap:
		print(row)
	return res	


def load_ptrns_banks(source, scene_id):
	scene_start = source.read_l(0x94b2 + 4*scene_id)
	source.set_pos(scene_start)
	while True:
		bank_id = source.read_w()
		if bank_id == 0xffff:
			break

		vpos = source.read_w()

		source.push()
		dec = load_ptrns_bank(source, bank_id)
		source.pop()
		dec.set_pos(0)
		load_ptrns(dec, vpos//32, len(dec)//32)

def load_bitmap(res):
	surf = np.zeros((8, 8), dtype=np.uint8)
	
	for y in range(8):
		v = res.read_b()
		for x in range(8):
			if v & 0x80:
				surf[y, x] = 1
			v = v << 1
	return surf
				
def load_bitmaps(res, t_id, nb_ptrns):
	print("load_ptrns(t_id=%x, nb_ptrns=%x)" % (t_id, nb_ptrns))
	for _ in range(nb_ptrns):
		tile = load_bitmap(res)
		patterns[t_id] = tile
		t_id += 1


# ===========================================================================

source = Buffer.load("roms/Juusou Kihei Leynos (Japan).md")

if False:
	source.set_pos(0x1b142)
	load_palette(0, 16, transparency=False)
	
	scene_start = source.read_l(0x94b2)
	source.set_pos(scene_start)
	while True:
		bank_id = source.read_w()
		if bank_id == 0xffff:
			break

		vpos = source.read_w()

		source.push()
		dec = load_ptrns_bank(source, bank_id)
		source.pop()
		dec.set_pos(0)
		load_ptrns(dec, vpos//32, len(dec)//32)

	save_vram("dump/scene_00.png", palette)

	
	# sega logo
	source.set_pos(0x1bc56)
	tm = fun_12162(source, 14, 12, 0xc000, 0x317, 2)
	surf = build_tilemap(tm)	
	save_png8(surf, palette, "dump/tm_1bc56.png")
	
	# title 1	
	source.set_pos(0x1b352)
#	tm = decompress_tilemap(source, 0x12d, 0)
	tm = fun_12162(source, 0, 0, 0xc000, 0x12d, 0)
#	save_png8(tm, palette, "dump/tm.png")
	surf = build_tilemap(tm)	
	save_png8(surf, palette, "dump/tm_1b352.png")
	
	# title 2
	source.set_pos(0x1b69c)
	tm = fun_12162(source, 40, 0, 0xc000, 0x12d, 0)
	surf = build_tilemap(tm)	
	save_png8(surf, palette, "dump/tm_1b69c.png")
	
	# title 3
	source.set_pos(0x1d4ea)
	tm = fun_12162(source, 4, 0, 0xe000, 0x81d2, 2)
	surf = build_tilemap(tm)	
	save_png8(surf, palette, "dump/tm_1d4ea.png")

if False:
	source.set_pos(0x1b142)
	load_palette(0, 16, transparency=False)
	
	scene_id = 8
	load_ptrns_banks(source, scene_id)

	# 	
	source.set_pos(0x108b4)
	tm = fun_12162(source, 14, 8, 0xc000, 0x8000, 0)
	surf = build_tilemap(tm)	
	save_png8(surf, palette, "dump/tm_108b4.png")
	
	# 	
	source.set_pos(0x104ae)
	tm = fun_12162(source, 0, 0, 0xe000, 0x809e, 0)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_104ae.png")
	

if False:
	source.set_pos(0x1b142)
	load_palette(0, 16, transparency=False)
	
	load_ptrns_banks(source, 1)
	load_ptrns_banks(source, 2)

	# 	
	source.set_pos(0x14d36)
	tm = fun_12162(source, 0, 22, 0xb000, 0x84c3, 0)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_14d36.png")

	# 	
	source.set_pos(0x14e12)
	tm = fun_12162(source, 4, 23, 0xb000, 0x84ec, 0)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_14e12.png")

	# 	
	source.set_pos(0x139c8)
	tm = fun_12162(source, 31, 23, 0xb000, 0x84ec, 1)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_139c8.png")

	# 	
	source.set_pos(0x14dc2)
	tm = fun_12162(source, 20, 23, 0xb000, 0x84c3, 0)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_14dc2.png")

	# 	
	source.set_pos(0xda22)
	tm = fun_12162(source, 2, 3, 0xc000, 0x8144, 2)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_da22.png")

	load_ptrns_banks(source, 6)

	# ???
	source.set_pos(0x13968)
	tm = fun_12162(source, 0, 0, 0xc000, 0x852b, 0)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_13968_1.png")

	# ???
	source.set_pos(0x13968)
	tm = fun_12162(source, 0, 0, 0xe000, 0, 0)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_13968_2.png")

	# 
	source.set_pos(0x157f4)
	tm = fun_12162(source, 0, 22, 0xb000, 0x84c3, 0)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_157f4.png")

	# ???
	source.set_pos(0x14ebe)
	tm = fun_12162(source, 2, 23, 0xb000, 0x85c6, 2)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_14ebe.png")

	# ???
	source.set_pos(0x139c8)
	tm = fun_12162(source, 2, 2, 0xc000, 0x84ec, 1)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_139c8.png")

	# 
	source.set_pos(0x139c8)
	tm = fun_12162(source, 2, 2, 0xc000, 0x84ec, 1)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_139c8.png")

	# 
	source.set_pos(0x13982)
	tm = fun_12162(source, 29, 18, 0xc000, 0x83e8, 0)
	surf = build_tilemap(tm)
	save_png8(surf, palette, "dump/tm_13982.png")


encoding =\
""" 0123456789ABCDEFGHIJKLMNOPQRSTU"""\
"""VWXYZabcdefghijklmnopqrstuvwxyzあ"""\
"""いうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむ"""\
"""めもやゆよらりるれろわをんがぎぐげござじずぜぞだづでどばびぶべぼ"""\
"""ぱぁぇゃゅょっアイウエカキクコサシスタチツテトナニネノハフマムメ"""\
"""ラリルレロワンガギグゴザズゾダデドバビブボパポァッャ!?,。-_"""\
""".'"""

if False:
	source.set_pos(0x8cb2)
	load_bitmaps(source, 0, 256)

	res = np.zeros((512, 256), dtype=np.uint8)
	x = y = 0
	for i in range(195):
		c = source.read_b(0x168d2 + 2*i)
		draw_ptrn(res, x, y, c)
		c = source.read_b(0x168d2 + 2*i + 1)
		draw_ptrn(res, x, y + 8, c)
		x += 8
		if x >= 256:
			y += 16
			x = 0
	
	save_png8(res, palette, "dump/font.png")
	
	res = np.zeros((512, 256), dtype=np.uint8)
	output = []
	
	source.set_pos(0x1dfbc)

	while source.pos < 0x1efc3:
		text = []
		res[:] = 0
		if source.read_b(pos=source.pos) == 0:
			source.pos += 1
	
		pos = source.pos
		code = source.read_b()
#		print("%x: first byte=%02x" % (pos, code))
		text.append("[%02x]" % code)

		output.append("; pos=0x%x" % pos)

		if code in [0x81, 0xfe]:
			output.append("[%02x]" % code)
			output.append("")
			continue

		# 1e048, 1e074, 1e0bf, 1e174
		x = y = 0
		while True:
			i = source.read_b()
			
						
			
			if i == 0xff:
				text.append("[ff]")
				break
			
			if i >= len(encoding):
				print("char [%02x] not found at pos 0x%x" % (i, source.pos - 1))
			text.append(encoding[i])

			c = source.read_b(0x168d2 + 2*i)
			draw_ptrn(res, x, y, c)
			c = source.read_b(0x168d2 + 2*i + 1)
			draw_ptrn(res, x, y + 8, c)
			x += 8
			if x >= 256:
				y += 16
				x = 0
		
#		if source.read_b(source.pos) in [0x81, 0xfe]:
#			text.append("[%02x]" % source.read_b(source.pos))
#			source.pos += 1
		
		output.append("".join(text))
		output.append("")
		save_png8(res, palette, "dump/text%x.png" % pos)

	with open("dump/script.txt", "w", encoding="utf8") as f:
		f.write("\n".join(output))

if True:
	source.set_pos(0x8338)
	load_palette(0, 16, transparency=True)
	
	scene_start = 0x9622
	source.set_pos(scene_start)
	while True:
		bank_id = source.read_w()
		print("bank %x" % bank_id)
		if bank_id == 0xffff:
			break

		vpos = source.read_w()

		source.push()
		dec = load_ptrns_bank(source, bank_id)
		source.pop()
		dec.set_pos(0)
		load_ptrns(dec, vpos//32, len(dec)//32)

	save_vram("dump/stage_screen.png", palette)
	pos = 0x104ae
	source.set_pos(pos)
	tm = decompress_tilemap(source, 0x809e)	
	save_png8(tm, palette, "dump/tm_%x.png" % pos)
	
	# 
	for pos in [0x108b4]: #, 0x108ec, 0x1091e, 0x10956, 0x1098c, 0x109be, 0x109c9]:
		source.set_pos(pos)
		tm = fun_12162(source, 14, 8, 0xc000, 0x8000, 2)
#		surf = build_tilemap(tm, 26, 13)	
		surf = build_tilemap(tm, 32, 32)	
		save_png8(surf, palette, "dump/tm_%x.png" % pos)


