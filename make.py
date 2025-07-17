# -*- coding: utf-8 -*-


from buffer import Buffer
from utils import load_from_png8, save_png8, TileSet, surface_to_tilemap
import numpy as np
import os

np.set_printoptions(formatter={'int':hex})
verbose = False
warnings=[]

def warns(warning):
	warnings.append(warning)

def print_warnings():
	print("Warnings:")
	for warning in warnings:
		print("\t%s" % warning)

palette = [
	(0, 0, 0), (0, 0, 255), (0, 255, 0), (0, 255, 255), (255, 0, 0), (255, 0, 255), (255, 255, 0), (255, 255, 255), 
	(128, 128, 128), (0, 0, 128), (0, 128, 0), (0, 128, 128), (128, 0, 0), (128, 0, 128), (128, 128, 0), (192, 192, 192)
]*8

# ============================================================================

encoding =\
""" 0123456789ABCDEFGHIJKLMNOPQRSTU"""\
"""VWXYZabcdefghijklmnopqrstuvwxyzあ"""\
"""ÁÀÂÇÉÈÊËÍÎÏÓÔÚÙÛÜŒÆÑにぬねのはひふへほまみむ"""\
"""áàâçéèêëíîïóôúùûüæœñずぜぞだづでどばびぶべぼ"""\
"""ぱぁぇゃゅょっアイウエカキクコサシスタチツテトナニネノハフマムメ"""\
"""ラリルレロワンガギグゴザズゾダデドバビブボパポァ¡¿!?,.-_"""\
"""。'"«»"""


def get_tag(line, tag):
#	print(line, tag)
	i = line.index(tag)
	j = line.index("=", i + len(tag))
	k = j + 1
	sep_level = 0
	while k < len(line):
		c = line[k]
		k += 1
		if c == ",":
			break
		if c == "[":
			sep_level += 1
			while True:
				c = line[k]
				k += 1
				if c == "[":
					sep_level += 1
				elif c == "]":
					sep_level -= 1
					if sep_level == 0:
						break
				
	#	print(i, j, k, line[i:j], line[j:k])
	return line[j + 1 : k - 1].strip()
	
def list_of_int(l):
	l = l.strip("[]")
	if l:
		return [int(x.strip(), 16) for x in l.split(",")]
	else:
		return []

def load_script(res, path):
	with open(path, encoding="utf8") as f:
		lines = f.readlines()
	
	i = 0
	pos = -1
	text = []
	width = height = -1

	while i < len(lines):
		while i < len(lines):
			line = lines[i].strip()
#			print(line)
			if not line.startswith(";"):
				break
#			print(i, "comment:", line)

			if "pos=" in line:
				pos = int(get_tag(line, "pos"), 16)
			if "width=" in line:
				width = int(get_tag(line, "width"))
			if "height=" in line:
				height = int(get_tag(line, "height"))
			if "ptrs=" in line:
				ptrs = list_of_int(get_tag(line, "ptrs"))
			else:
				ptrs = []
			i += 1
		
		while i < len(lines):
			line = lines[i].rstrip()
			if line == "":
				if pos in res:
					warns("text at 0x%x already defined" % pos)
				else:
					if height == -1:
						res[pos] = {"text": "".join(text), "pos": pos, "width": width, "height": height, "ptrs": ptrs}
					else:
						res[pos] = {"text": "\n".join(text), "pos": pos, "width": width, "height": height, "ptrs": ptrs}
				text = []
				width = height = -1
#				print("res=%s" % res)
				break
#			print(i, "text:", line)
			text.append(line)
			i += 1

		while i < len(lines):
			line = lines[i].strip()
#			print(i, "blank:", line)
			if line != "":
				break
			i += 1

	return res

def encode_text(text):
	res = []
	i = 0
	while i < len(text):
		t = text[i]
		i += 1
		
		if t == "[":
			j = text.index("]", i)
			c = int(text[i : j], 16)
			i = j + 1
		
		elif t not in encoding:
			warns('char |%s| not found in text "%s"' % (t, text))
#			raise Exception()

		else:
			c = encoding.index(t)
		res.append(c)
	return res


# ============================================================================

def encode_stage_text(lines):
	width = max([len(line) for line in lines])
	height = len(lines)
	
	res = [] # np.zeros((height, width), dtype=np.uint8)
	
	for text in lines:
		row1 = []
		row2 = []
		dx = (width - len(text))//2
		for _ in range(dx):
			row1.append(0)
			row2.append(0)

		i = 0
		while i < len(text):
			t = text[i]
			i += 1
			
			if t == "[":
				j = text.index("]", i)
				c = int(text[i : j], 16)
				i = j + 1
			
			elif t not in encoding:
				warns('char |%s| not found in text "%d"' % (t, text))
	
			else:
				c = encoding.index(t)

			t1 = source.read_b(0x168d2 + 2*c)
			t2 = source.read_b(0x168d2 + 2*c + 1)

			row1.append(t1)
			row2.append(t2)

		for _ in range(width - dx - len(text)):
			row1.append(0)
			row2.append(0)
		
		res += row1 + row2

	return res


def write_ptrn(buf, ptrn):
	ptrn32 = np.array(ptrn, dtype=np.uint32)
	ptrn_data = ((ptrn32[:,0] & 15) << 28) | ((ptrn32[:,1] & 15) << 24) | ((ptrn32[:,2] & 15) << 20) | ((ptrn32[:,3] & 15) << 16) | ((ptrn32[:,4] & 15) << 12) | ((ptrn32[:,5] & 15) << 8) | ((ptrn32[:,6] & 15) << 4) | ((ptrn32[:,7] & 15) << 0)
	for d in ptrn_data:
		buf.write_l(d)

def write_ptrns(buf, surf):
	pos = buf.pos
	h, w = surf.shape
	for y in range(0, h, 8):
		for x in range(0, w, 8):
			write_ptrn(buf, surf[y:y+8, x:x+8])
	return pos


def compress_gfx(src):
	res = Buffer()
	nb_ptrns = len(src)//32
	res.write_b(nb_ptrns & 0xff)
	res.write_b(nb_ptrns // 256)

	src.set_pos(0)
	res.write(src)

	return res

def compress_tilemap(src, width, height):

	res = Buffer()
	res.write_b(1)
	res.write_b(width)
	res.write_b(height)

	def ship(val, count):
		
		if val == -1:
			return
		if val >= 0xf9:
			for _ in range(count):
				res.write_b(0xf9)
				res.write_w(val)
		elif count == 1:
			res.write_b(val)
		elif count == 2:
			res.write_b(val & 0xff)
			res.write_b(val & 0xff)
		else:
			res.write_b(0xfe)
			res.write_b(count)
			res.write_b(val & 0xff)
	
	src.set_pos(0)
	flip_flags = -1
	last_val = -1
	count = 0
	
	for _ in range(width*height):
		val = src.read_w()
		ff = val & 0x1800
		val = val & 0x7ff
		if ff != flip_flags:
			ship(last_val, count)
			flip_flags = ff
			if ff == 0:
				res.write_b(0xfd)
			elif ff == 0x800:
				res.write_b(0xfc)
			elif ff == 0x1000:
				res.write_b(0xfb)
			elif ff == 0x1800:
				res.write_b(0xfa)
			
			last_val = val
			count = 1
		
		elif val != last_val:
			ship(last_val, count)
			count = 1
			last_val = val
		
		else:
			count += 1

	ship(last_val, count)
	res.write_b(0xff)

	return res

def print_surf(surf, x, y, text):
	for c in text:
		i = encoding.index(c)
		surf[y : y + 16, x : x + 8] = chars[i]*15
		x += 8

def build_tilemaps(buf, surfs, base_ptrn=0, include_blank=False, blank_id=-1, tileset=None):
	tilemaps = []

	if tileset is None:
		tileset = TileSet([])
	
	if include_blank:
		tileset.append(np.zeros((8, 8), dtype=np.uint8))


	for surf in surfs:
		height, width = surf.shape
		
		tm = surface_to_tilemap(surf, tileset, blank_id)
	
		dec = Buffer()
		for row in tm:
#			print(" ".join(["%04x" % (base_ptrn + x) for x in row]))
			for tile_id in row:
				dec.write_w(base_ptrn + tile_id)
		
		comp = compress_tilemap(dec, width//8, height//8)
		tilemaps.append(comp)
		
	dec = Buffer()
	for tile in tileset:
		write_ptrn(dec, tile)
	
	comp = compress_gfx(dec)
	return comp, tilemaps

# ============================================================================

def to_md(c):
	r, g, b = c # (c >> 16) & 255, (c >> 8) & 255, c & 255
	r1, g1, b1 = r//32, g//32, b//32
	return (b1 << 9) + (g1 << 5) + (r1 << 1)

def write_palette(src, pal):
	for c in pal:
		src.write_w(to_md(c))

# ============================================================================

def make_font(surf, encoding, widthes, sizechar=(16, 16)):
	symbols["fontBitmaps"] = source.pos

	cw, ch = sizechar
	fh, fw = surf.shape
	x, y = 0, 0
	chars = []
	
	for c, w in zip(encoding, widthes):
#		print("c=|%s| width=%d" % (c, w))
		char = surf[y:y+ch, x:x+cw]
		x += cw

		if c == " ":
			left = 0
			right = w - 2
		else:
			if x == fw:
				y += ch
				x = 0
			left = 0
#			while left < cw-1 and (char[:, left] == 0).all():
#				left += 1
			if left == cw-1:
				left = 0
				right = cw-2
			else:
				right = cw-1
				while (char[:, right] == 0).all():
					right -= 1
#			print("%s: left=%d right=%d" % (c, left, right))
			
		width = min(16, right - left + 2)
		char_pixmap = np.zeros((ch, cw), dtype=np.uint8)
	#	char_pixmap[:] = 0
		ch_ = min(ch, 16)
		char_pixmap[:ch_,:width - 1] = char[:ch_, left:left + width - 1] != 0
#		save_png8(char_pixmap, palette, "dbg(%s)c.png" % c)
		
		char_bitmap = (char_pixmap[0,:] * 0x8000) + (char_pixmap[1,:] * 0x4000) + (char_pixmap[2,:] * 0x2000) + (char_pixmap[3,:] * 0x1000) + (char_pixmap[4,:] * 0x800) + (char_pixmap[5,:] * 0x400) + (char_pixmap[6,:] * 0x200) + (char_pixmap[7,:] * 0x100) + (char_pixmap[8,:] * 0x80) + (char_pixmap[9,:] * 0x40) + (char_pixmap[10,:] * 0x20) + (char_pixmap[11,:] * 0x10) + (char_pixmap[12,:] * 8) + (char_pixmap[13,:] * 4) + (char_pixmap[14,:] * 2) + (char_pixmap[15,:] * 1)
		for data in char_bitmap:
			source.write_w(data)
		chars.append(char_pixmap)
#		assert w == width

	symbols["widthTable"] = source.pos
	for w in widthes:
		source.write_b(w)
	source.align()

	return char


# ============================================================================

source = Buffer.load("roms/Juusou Kihei Leynos (Japan).md")


if True:
	print("enlarging ROM")
	symbols = {}
	source.set_size(0x100000)
	source.set_pos(0x80000)

if True:
	print("generating mission intro names")

	surf, _ = load_from_png8("res/font.png")
	chars = []
	x = y = 0
	for _ in encoding:
		chars.append(surf[y : y + 16, x : x + 8])
		x += 8
		if x >= 256:
			x = 0
			y += 16

	surfs = []
	width, height = 144, 32
	i = 0
	for lines in [
		["STAGE 1", "Raid on Ganymede"], 
		["STAGE 2", "Escape"],
		["STAGE 3", "Orbital Attack"],
		["STAGE 4", "Front Line Assault"],
		["STAGE 5", "Surprise Attack"],
		["STAGE 6", "Headquarter Blitz"],
		["STAGE 7", "Space Colony Smash"],
		["STAGE 8", "The Final Conflict"]
	]:
		surf = np.zeros((height, width), dtype=np.uint8)		
		surfs.append(surf)
		y = 0
		for line in lines:
			x = 8*(width//8 - len(line))//2
			print_surf(surf, x, y, line)
			y += 16
		i += 1
#		save_png8(surf, palette, "temp/STAGE %d.png" % i)
	
	patterns, tilemaps = build_tilemaps(
		source, 
		surfs,
		base_ptrn=0
	)

	ptrns_pos = source.pos
	source.write_l(ptrns_pos, 0x3d944)
	source.write(patterns)	

	source.align()
	
	for tm, ptr in zip(tilemaps, [0xeba0, 0xec38, 0xecda, 0xed84, 0xef56, 0xeff6, 0xf14c, 0xf228]):
		tm_pos = source.pos
		source.write_l(tm_pos, ptr)
		source.write(tm)
		source.align()

if True:
	print("generating font")
	widthes = [
		4, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 
		8, 8, 8, 7, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8,
		8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 4, 8, 8, 
		4, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 
		8, 8, 8, 8, 8, 8, 8, 8, 7, 7, 7, 8, 8, 8, 8, 8, 
		8, 15, 15, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 
		8, 8, 8, 8, 8, 8, 8, 8, 4, 4, 4, 8, 8, 8, 8, 8, 
		8, 15, 15, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 
		8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 
		8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 
		8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 
		8, 8, 8, 8, 8, 8, 8, 8, 3, 8, 3, 8, 3, 3, 8, 8,
		3, 2, 4, 6, 6
	]

	font, _ = load_from_png8("res/vwf.png")
	chars = make_font(font, encoding, widthes)
	source.align()
#	raise Exception()

if True:
	print("inserting script")
	script = {}
	load_script(script, "res/script-VWF.txt")
	
	for pos in script:
		encoded = encode_text(script[pos]["text"])
		source.align()
		
		new_pos = source.pos
		for c in encoded:
			source.write_b(c)
		
		if "ptrs" in script[pos]:
			for ptr in script[pos]["ptrs"]:
				assert(source.read_l(ptr) == pos)
				source.write_l(new_pos, ptr)

if True:
	print("moving patterns banks descriptors")
	source.align()
	ptrs_to_banks_descriptors = source.pos 
	for i in range(32):
		source.write_l(source.read_l(0x94b2 + i*4))
	extra_ptrs_to_bank_descriptors = source.pos
	for _ in range(10):
		source.write_l(0)

	source.write_l(ptrs_to_banks_descriptors, 0x88dc)
	source.write_l(ptrs_to_banks_descriptors, 0x8afc)
	

	ptrs_to_patterns = source.pos
	for i in range(96):
		source.write_l(source.read_l(0x3d800 + i*4))
	extra_ptrs_to_patterns = source.pos
	for _ in range(10):
		source.write_l(0)

	for ptr in [0x89e8, 0x8b46]:
		source.write_l(ptrs_to_patterns, ptr)
	for ptr in [0x15018, 0x15268]:
		source.write_l(ptrs_to_patterns + 0x10c, ptr)
	for ptr in [0x1502e, 0x1527e]:
		source.write_l(ptrs_to_patterns + 0x110, ptr)

if True:
	print("generating mission intro pictures")
	for i in range(8):
		mission_id = i + 1
		surf, pal = load_from_png8("res/bgStage%d.png" % mission_id)
		pal[0] = (0, 0, 0)
	
		patterns, tilemaps = build_tilemaps(
			source, 
			[
				surf
		    ],
			base_ptrn=0
		)
	
		source.align()
		ptrns_pos = source.pos
		source.write_l(ptrns_pos, extra_ptrs_to_patterns + 4*i)
		source.write(patterns)
#		patterns.save("temp/patterns%x.bin" % ptrns_pos)
	
		source.align()
		descr_pos = source.pos
		source.write("00 27 9d 80 00 51 00 00 00 %02x 13 c0 ff ff" % (0x60 + i))
		source.write_l(descr_pos, extra_ptrs_to_bank_descriptors + 4*i)
	
		tm = tilemaps[0]
		source.align()	
		tm_pos = source.pos
		symbols["TM_mission_intro_%d_bg" % mission_id] = tm_pos
		source.write(tm)
#		tm.save("temp/tilemap%d.bin" % mission_id)
		source.align()
		
		
		symbols["PAL_mission_intro_%d_bg" % mission_id] = source.pos
		write_palette(source, pal[:16])

if True:
	print("inserting asm hacks")
	source.align()
	symbols["hackStart"] = source.pos
	source.include("asm/hack.asm", symbols)

if True:
	print("fixing header")
	# ROM end
	source.write_l(0xfffff, 0x1a4)


source.save("roms/out.md")
# Invincible
source.write("4e71 4e71", 0x4dce)
source.save("roms/out-invulnerable.md")

print_warnings()