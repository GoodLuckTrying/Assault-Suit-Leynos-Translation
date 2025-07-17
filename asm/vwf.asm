VDP_ctrlPort	equ	0xc00004
VDP_dataPort	equ	0xc00000

ptrnBuffer	equ	0xffa800 ; 3000
shift	equ	0xffa840 ; 3040
currentPtrnId	equ	0xffa842 ; 3042
leftText	equ	0xffa844 ; 3044
widthText	equ	0xffa846 ; 3046

bgTextColor	equ	0xffa848 ; 3048
fgTextColor	equ	0xffa84a ; 304a

sfxId	equ	0xffff8088
currentText	equ	0xffffb784


; =====================================================
; vwf

drawNextChar

		; d3 = char
		movem.l		d0-d7/a1/a2/a3/a4, -(sp)
		lea		widthTable, a1
		lea		fontBitmaps, a2
		
		move.w		shift, d2		; d2 = shift
		
		moveq		#7, d4
		sub.w		d2, d4
		asl.w		#2, d4			; d4 = pixel shift
		
		moveq		#0, d7
		move.b		(a1, d3), d7		; d7 = width of char
		subq		#1, d7
		
		asl.w		#5, d3		; 32 bytes = 16*16 bits/pixels
		lea		(a2, d3), a4
		
@next_column
		moveq		#15, d5			; d5 = nb of row
		lea		ptrnBuffer, a3
		move.w		(a4)+, d0		; d0 = pixel row

@next_pixel_row		
		moveq		#0, d1
		move.b		bgTextColor, d1
		lsl.l		d4, d1
		eor.l		d1, (a3)

		lsl.w		#1, d0
		bcc		@continue
		move		#0, d1
		move.b		fgTextColor, d1
		lsl.l		d4, d1
@continue:
		or.l		d1, (a3)+
		dbf		d5, @next_pixel_row

		subq		#4, d4
		addq		#1, d2
		cmp.w		#8, d2
		bne		@dont_send
		bsr		sendAndAdvance
		
@dont_send
		dbf		d7, @next_column
		
		bsr		send
		move.w		d2, shift

		movem.l		(sp)+, d0-d7/a1/a2/a3/a4
		rts

clearBuffer
		movem.l		d0/a3, -(sp)
		lea		ptrnBuffer, a3

		move.b		bgTextColor, d1
		move.b		d1, d0
		lsl.w		#4, d0
		or.b		d1, d0
		move.b		d0, d1
		lsl.w		#8, d1
		move.b		d0, d1
		move.w		d1, d0
		swap		d1
		move.w		d0, d1

		moveq		#15, d0

@next:
		move.l		d1, (a3)+
		dbf		d0, @next
		add.w		#0x40, currentPtrnId
		moveq		#0, d2
		move.w		d2, shift
		moveq		#28, d4
		movem.l		(sp)+, a3/d0
		rts

; clearTextArea
		; ori		#0x700, sr
		; move.l		#0x60000000, (VDP_ctrlPort)
		; move.w		#0x3ff, d1
		; bsr		clearTextArea_
		; move.w		#0x2000, currentPtrnId
		; move.w		#0x2000, leftText
;;		andi		#0xf8ff, sr
		; rts

; clearTextArea_
		; move.b		bgTextColor, d1
		; move.b		d1, d0
		; lsl.w		#4, d0
		; or.b		d1, d0
		; move.b		d0, d1
		; lsl.w		#8, d1
		; move.b		d0, d1
		; move.w		d1, d0
		; swap		d1
		; move.w		d0, d1

; @loop
		; move.l		d0, (VDP_dataPort)
		; dbra		d1, @loop
		
		; moveq		#15, d1
		; lea		ptrnBuffer, a6
; @next
		; move.l		d0, (a6)+
		; dbra		d1, @next

		; move.w		#0, shift
		; rts

send:
		; currentPtrnId
		; CDx = 00001 (VRAM write)
		; Ax = 0x2000 = 00100000 00000000 00000000 00000000
		; CD1 CD0 A13 A12 A11 A10 A09 A08 (D31-D24)
		; A07 A06 A05 A04 A03 A02 A01 A00 (D23-D16)
		; ? ? ? ? ? ? ? ? (D15-D8)
		; CD5 CD4 CD3 CD2 ? ? A15 A14 (D7-D0)
		
		movem.l		a3, -(sp)

		move.w		currentPtrnId, d0
		and.l		#0xffff, d0
		move.l		d0, d3
		rol.w		#2, d3
		andi		#3, d3
		andi.w		#0x3fff, d0
		swap		d0
		or.w		d3, d0
		ori.l		#0x40000000, d0 ; !!!!!!
		ori		#0x700, sr
		
		move.l		d0, (VDP_ctrlPort)
		
		lea		ptrnBuffer, a3
		moveq		#15, d0
@next:		; send pattern and clear buffer
		move.l		(a3)+, (VDP_dataPort)
		dbf		d0, @next
		
		andi		#0xf8ff, sr

		movem.l		(sp)+, a3
		rts

sendAndAdvance
		bsr		send
		bsr		clearBuffer
		rts
		











; ==================================================

; init VWFBuffer
lbl_11d96
	movem.l	d2, -(sp)
	move.w	#4, (0xffffb780).l
	move.w	d1, (0xffffb782).l
	move.l	a1, currentText

	move.b	#14, bgTextColor
	move.b	#15, fgTextColor

	move.w	#0, shift
	jsr	clearBuffer

	movem.l	(sp)+, d2	
	rts


; draw new char
lbl_11dac
	movem.l	a1/d2/d1, -(sp)
	subq.w	#1, (0xffffb780).w
	bne	@not_yet
	move.w	#4, d1
	tst.w	(0xffffb774).l
	bne	@continue
	tst.b	(0xffff8048).w
	beq	@continue
	move.w	#1, d1
@continue
	move.w	d1, (0xffffb780).w
	movea.l	currentText, a1
	clr.w	d3
	move.b	(a1), d3
	cmpi.b	#-1, d3
	beq.b	@end_of_line

	move.w	(0xffffb782).w, d2
	lsl.w	#1, d2
	add.w	#0x7c0, d2
	lsl.w	#5, d2
	move.w	d2, currentPtrnId
	jsr	drawNextChar
	move.w	currentPtrnId, d2
	lsr.w	#5, d2
	sub.w	#0x7c0, d2
	lsr.w	#1, d2
	move.w	d2, (0xffffb782).w
	
	move.w	#1, (sfxId)

	addq.l	#1, currentText.w
@not_yet
	clr.w	d0
	cmpi.w	#0x1e, (0xffffb782).w
	bne.b	@return
@end_of_line
	moveq	#1, d0
@return
	movem.l	(sp)+, d1/d2/a1
	rts

