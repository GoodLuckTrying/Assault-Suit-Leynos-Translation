fontBitmaps equ 528156
widthTable equ 534460
TM_mission_intro_1_bg equ 546716
PAL_mission_intro_1_bg equ 547826
TM_mission_intro_2_bg equ 558628
PAL_mission_intro_2_bg equ 559822
TM_mission_intro_3_bg equ 567904
PAL_mission_intro_3_bg equ 568948
TM_mission_intro_4_bg equ 573062
PAL_mission_intro_4_bg equ 574116
TM_mission_intro_5_bg equ 584918
PAL_mission_intro_5_bg equ 586304
TM_mission_intro_6_bg equ 601906
PAL_mission_intro_6_bg equ 603354
TM_mission_intro_7_bg equ 607628
PAL_mission_intro_7_bg equ 608724
TM_mission_intro_8_bg equ 627014
PAL_mission_intro_8_bg equ 628470
hackStart equ 628502
loadPatternsBanks	equ	0x8af8
loadTilemap	equ	0x12162

missionId	equ	0xffff805a

	; bypass checksum
	org	0x8124
	bra	0x8150

	org	0x8b4a
	jmp	loc_8b4a

	; mission intro screen
	org	0x10396
	jmp	loc_10396

	; mission intro palettes	
	org	0x103f0
	jmp	loc_103f0

	; init VWF
	org	0x11d96
	jmp	lbl_11d96

	; draw new char
	org	0x11dac
	jmp	lbl_11dac

	; tilemap loader
	org	0x12220
	jmp	loc_12220
	
	org	0x13c28
	jmp	loc_13c28
	
	org	hackStart
	include	"asm/vwf.asm"


TM_mission_intro_bgs
	dc.l	TM_mission_intro_1_bg
	dc.l	TM_mission_intro_2_bg
	dc.l	TM_mission_intro_3_bg
	dc.l	TM_mission_intro_4_bg
	dc.l	TM_mission_intro_5_bg
	dc.l	TM_mission_intro_6_bg
	dc.l	TM_mission_intro_7_bg
	dc.l	TM_mission_intro_8_bg

; load mission intro screen according to mission number
loc_10396
	moveq	#32, d5
	add.w	missionId, d5
	jsr	loadPatternsBanks

	move.w	#0x78, (0xffffb73c).w
	movea.l	(sp)+, a1
	moveq	#14, d1
	moveq	#8, d2
	move.w	#0x8000, d4
	moveq	#0, d5
	moveq	#0, d6
	move.w	#0xC000, d3
	jsr	loadTilemap
	lea	TM_mission_intro_bgs, a1
	moveq	#0, d0
	move.w	missionId, d0
	lsl.w	#2, d0
	movea.l	(a1, d0), a1
	moveq	#0, d1
	moveq	#0, d2
	move.w	#0x809e, d4
	moveq	#0, d5
	clr.w	d6
	move.w	#0xe000, d3
	jsr	loadTilemap

	jmp	0x103d0
	
PAL_mission_intro_bgs
	dc.l	PAL_mission_intro_1_bg
	dc.l	PAL_mission_intro_2_bg
	dc.l	PAL_mission_intro_3_bg
	dc.l	PAL_mission_intro_4_bg
	dc.l	PAL_mission_intro_5_bg
	dc.l	PAL_mission_intro_6_bg
	dc.l	PAL_mission_intro_7_bg
	dc.l	PAL_mission_intro_8_bg

; load mission intro palettes	
loc_103f0
	lea	PAL_mission_intro_bgs, a1
	moveq	#0, d0
	move.w	missionId, d0
	lsl.w	#2, d0
	move.l	(a1, d0), (0xffffb7ca).w
	movem.l	(sp)+, a1
	jmp	0x103fc

; increment missionId in order to load intro screen
loc_13c28
	add.w	#1, missionId
	move.l	#0x13d36, (0xff8000).l
	rts

; modify patterns bank format
; original is nnnnnnnn xxxxxxxx where n=number of tiles, xxxxxxxx=0 if uncompressed (with last 4 bits always 0)
; new is nnnnnnnn xxxxnnnn where xxxx0000 is same as above, and n=number if tiles can go up to 0xfff
loc_8b4a
	movea.l	(a1, d0), a0
	move.b	1(a0), d6
	lsl.w	#8, d6
	move.b	(a0), d6
	addq.l	#2, a0
	move.w	d6, d1
	andi.w	#0xfff, d6
	andi.w	#0xf000, d1
	lsr.w	#8, d1
	jmp	0x8b52


; loadTilemap improvement: allow f9 code to load tile_id >= 0x100
loc_12220
	clr.w	d2
	move.b	(a1), d2
	cmpi.b	#0xff, d2
	beq	@code_ff
	cmpi.b	#0xf9, d2
	beq	@code_f9
	jmp	0x1222c
	
@code_ff	jmp	0x122fa

@code_f9	
	move.b	1(a1), d2
	lsl.w	#8, d2
	move.b	2(a1), d2
	addq.l	#2, a1
	jmp	0x1228e

; write 00000042 in RAM to find free chunks (must be disabled)
loc_8170
	move.l	#0x00000042, d7
	move.w	#0x37ff, d6
@loop
	move.l	d7, (a6)+
	dbra	d6, @loop
	jmp	0x817c