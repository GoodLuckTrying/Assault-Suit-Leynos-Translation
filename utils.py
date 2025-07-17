# -*- coding: utf-8 -*-
"""
Created on Fri Nov  8 18:06:25 2024

@author: fterr
"""


import png
import numpy as np

def load_from_png8(path):
	r = png.Reader(filename=path)
	w, h, res, info = r.read()
	
	res = np.array(list(res), dtype=np.uint8)
	res.shape = (h, w)

	return res, info["palette"]

def save_png8(surf, palette, path):
	height, width = surf.shape
	w = png.Writer(width, height, palette=palette, bitdepth=8)
	with open(path, 'wb') as f:
		w.write(f, surf)



def compute_checksum(src):
	return src.sum()

def check_flips(ptrn_a, ptrn_b, ignore_flips = False):
	if ignore_flips:
		if (ptrn_a == ptrn_b).all():
			return (False, False)
	elif (ptrn_a == ptrn_b).all():
		return (False, False)
	elif (ptrn_a[::-1, :] == ptrn_b).all():
		return (True, False)
	elif (ptrn_a[:, ::-1] == ptrn_b).all():
		return (False, True)
	elif (ptrn_a[::-1, ::-1] == ptrn_b).all():
		return (True, True)			
	return None

class TileSet:
	def __init__(self, iterable):
		self.data = []
		self.checksums = []
		for tile in iterable:
			self.update_and_get(tile)

	def __iter__(self):
		return self.data.__iter__()
	
	def __next__(self):
		return self.data.__next__()

	def __len__(self):
		return len(self.data)

	def update_and_get(self, tile, verbose=False):
		checksum_a = compute_checksum(tile)
	
		for i, t in enumerate(self):
	#		print(t)
	#		print(tile_checksums[i])
			if verbose:
				print(t, tile)
			if self.checksums[i] == checksum_a and (checked := check_flips(t, tile)) is not None:
				vflip, hflip = checked
				return vflip*0x1000 + hflip*0x800 + i
		self.data.append(tile)
		self.checksums.append(checksum_a)
		return len(self.data) - 1

	def append(self, tile):
		self.update_and_get(tile)
	
	def save(self, path, palette=None):
		height = len(self) // 16
		if len(self) % 16:
			height += 1
		height *= 8
		
		surf = np.zeros((height, 128), dtype=np.uint8)
		x = y = 0
		for tile in self.data:
			surf[y : y + 8, x : x + 8] = tile
			x += 8
			if x == 128:
				x = 0
				y += 8
		
		if palette is None:
			palette = [
				(0, 0, 0), (253, 253, 253), (0, 253, 0), (0, 253, 253), (253, 0, 0), (253, 0, 253), (253, 253, 0), (253, 253, 253), 
				(126, 126, 126), (0, 0, 126), (0, 126, 0), (0, 126, 126), (126, 0, 0), (126, 0, 126), (126, 126, 0), (191, 191, 191)
			]*8
		
		save_png8(surf, palette, path)
		

def surface_to_tilemap(src, tileset=TileSet([]), blank_id=-1, tilesize=(8, 8)):
	tw, th = tilesize
	h, w = src.shape
	res = []
	for y in range(0, h, th):
		map_line = []
		for x in range(0, w, tw):
			src_tile = src[y : y + th, x : x + tw]
			if blank_id >= 0 and (src_tile == 0).all():
				map_line.append(blank_id)
				continue
			tile = tileset.update_and_get(src_tile, verbose=False)
			map_line.append(tile)
		res.append(map_line)
	return res
