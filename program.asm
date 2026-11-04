org 0x00
store [0x0088], r0
store [0x008C], r1
store [0x0090], r2
store [0x0094], r3
load r0, [0x0088]
load r1, [0x008C]
load r2, [0x0090]
load r3, [0x0094]
reti
org 0x100
int_enable
load r0, #11
store_byte [0x3004], r0
load r0, #104
store_byte [0x3005], r0
load r0, #101
store_byte [0x3006], r0
load r0, #108
store_byte [0x3007], r0
load r0, #108
store_byte [0x3008], r0
load r0, #111
store_byte [0x3009], r0
load r0, #32
store_byte [0x300A], r0
load r0, #119
store_byte [0x300B], r0
load r0, #111
store_byte [0x300C], r0
load r0, #114
store_byte [0x300D], r0
load r0, #108
store_byte [0x300E], r0
load r0, #100
store_byte [0x300F], r0
load r0, #0
store [0x3010], r0
while_0:
load r0, [0x3010]
load r2, #11
cmp r0, r2
jgt end_while_0
jeq end_while_0
load r0, #0x3005
load r3, [0x3010]
add r0, r0, r3
store [0x3014], r0
load r1, [0x3014]
load_byte r0, [r1]
store [0x3018], r0
load r0, [0x3018]
store_byte [0x84], r0
load r0, [0x3010]
load r3, #1
add r0, r0, r3
store [0x3010], r0
jmp while_0
end_while_0:
halt