; Pacman Display
;
; Each color in the pattern should travel like a Pacman
; to it's position. After all positions are filled, start over.

init:
    stall #10
    ldx $0      ; x will contain our LED count
    stx $10     ; $10 will contain our furthest position that's been loaded
    ldx #0
    stx $11     ; $11 contains the current pacman position
    ldx $1      ; number of LED colors in pattern
    dex         ; The first pacman color is the last in the pattern
    stx $12     ; Pacman color
    ldx #0      
    stx $13     ; Color index

start:
    ldx #0      ; start at LED 0 

led_loop:
    cpx $0
    beq finished

    cpx $11     ; Check if at pacman LED
    beq pacman_led

    ; If not at pacman, it will either be an OFF, or the color at that position
    cpx $10
    bmi led_off
led_on:
    ldy $13
    jmp write_color

led_off:
    ldy #3
    jmp write_color

pacman_led:
    ldy $12

write_color:
    sty $2      ; Write the color

    ldy $13
    iny
    cpy $1
    bne store_next_color

reset_color:
    ldy #0

store_next_color:
    sty $13

    inx
    jmp led_loop

finished:
    ldy $11     ; current pacman position
    iny
    cpy $10     ; is the pacman at the destination position?
    beq pacman_arrived

    sty $11     ; store next pacman position
    jmp next

pacman_arrived:
    ldy #0
    sty $11     ; reset pacman to 0

    ldy $10     
    dey
    beq init    ; if at end, restart, todo delay?
    sty $10     ; store new position

    ; update pacman color
    ldy $12
    beq roll_pacman_color
    dey
    sty $12
    jmp next

roll_pacman_color:
    ldy $1
    dey
    sty $12

next:
    stall #1
    jmp start
