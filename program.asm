org 0x00
store [0x0088], r0
store [0x008C], r1
store [0x0090], r2
store [0x0094], r3
load r0, R_INT
store [3004], r0
load r0, [3004]
load r1, [3000]
store_byte [0x4000+r1], r0
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
load r0, [r1]
store [3008], r0
load r0, [3008]
load r2, #1
cmp r0, r2
jgt end_if_0
jeq end_if_0
load r0, #-1
store [0x84], r0
jmp end_if_0
else_0:
load r0, [3008]
load r2, #1
cmp r0, r2
jne end_if_1
load r0, #0
store [0x84], r0
jmp end_if_1
else_1:
load r0, #0
store [300C], r0
load r0, #2
store [3010], r0
while_0:
load r0, [3010]
load r3, [3010]
mul r0, r0, r3
load r2, [3008]
cmp r0, r2
jgt end_while_0
load r0, [3008]
load r3, [3010]
mod r0, r0, r3
load r2, #0
cmp r0, r2
jne end_if_2
load r0, #1
store [300C], r0
jmp end_while_0
end_if_2:
load r0, [3010]
load r3, #1
add r0, r0, r3
store [3010], r0
jmp while_0
end_while_0:
load r0, [300C]
load r2, #1
cmp r0, r2
jne end_if_3
load r0, #0
store [0x84], r0
jmp end_if_3
else_3:
load r0, #1
store [0x84], r0
end_if_3:
end_if_1:
end_if_0:
halt