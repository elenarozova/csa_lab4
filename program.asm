org 0x00
store [0x0088], r0
store [0x008C], r1
store [0x0090], r2
store [0x0094], r3
load r0, R_INT
store [3004], r0
load r0, [3004]
load r1, [3000]
store_byte [0x4000 + r1], r0
load r0, [3000]
load r3, #1
add r0, r0, r3
store [3000], r0
load r0, [0x0088]
load r1, [0x008C]
load r2, [0x0090]
load r3, [0x0094]
reti
org 0x100
int_enable
load r1, #0x4000
load_byte r0, [r1]
store [3008], r0
load r0, #1
store [300C], r0
load r0, [3008]
load r3, #1
add r0, r0, r3
store [3008], r0
load r0, #0x4000
load r3, [3008]
add r0, r0, r3
store [3010], r0
while_0:
load r0, [300C]
load r2, [3008]
cmp r0, r2
jgt end_while_0
load r0, #0x4000
load r3, [300C]
add r0, r0, r3
store [3014], r0
load r1, [3014]
load_byte r0, [r1]
store [3018], r0
load r0, [3018]
load r2, #37
cmp r0, r2
jne end_if_0
load r0, [300C]
load r3, #1
add r0, r0, r3
store [300C], r0
load r0, [300C]
load r2, [3008]
cmp r0, r2
jgt end_if_1
load r1, [3014]
load_byte r0, [r1]
store [301C], r0
load r0, [301C]
load r2, #100
cmp r0, r2
jne end_if_2
load r1, [3010]
load r0, [r1]
store [3020], r0
load r0, [3010]
load r3, #4
add r0, r0, r3
store [3010], r0
load r0, [3020]
load r2, #0
cmp r0, r2
jgt end_if_3
jeq end_if_3
load r0, #45
store_byte [0x84], r0
load r0, #0
load r3, [3020]
sub r0, r0, r3
store [3020], r0
end_if_3:
load r0, [3020]
load r2, #0
cmp r0, r2
jne end_if_4
load r0, #48
store_byte [0x84], r0
jmp end_if_4
else_4:
load r0, #0x6000
store [3024], r0
load r0, #0x6000
store [3028], r0
while_1:
load r0, [3020]
load r2, #0
cmp r0, r2
jeq end_while_1
load r0, [3020]
load r3, #10
mod r0, r0, r3
load r3, #48
add r0, r0, r3
store [302C], r0
load r0, [302C]
store_byte [3028], r0
load r0, [3028]
load r3, #1
add r0, r0, r3
store [3028], r0
load r0, [3020]
load r3, #10
div r0, r0, r3
store [3020], r0
jmp while_1
end_while_1:
load r0, [3028]
load r3, #1
sub r0, r0, r3
store [3028], r0
while_2:
load r0, [3024]
load r2, [3028]
cmp r0, r2
jgt end_while_2
load r1, [3028]
load_byte r0, [r1]
store [302C], r0
load r0, [302C]
store_byte [0x84], r0
load r0, [3028]
load r3, #1
sub r0, r0, r3
store [3028], r0
jmp while_2
end_while_2:
end_if_4:
jmp end_if_0
else_0:
load r0, [301C]
store_byte [0x84], r0
end_if_0:
load r0, [300C]
load r3, #1
add r0, r0, r3
store [300C], r0
jmp while_0
end_while_0:
halt