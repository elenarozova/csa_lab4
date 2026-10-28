org 0x100

start:
    ;let digit = read_word(0x80)
    load r0, [0x80]
    store [digit], r0

    ;if (digit<1){
    cmp r0, 1
    jgt else1
    jeq else1

    ;print_word(-1, 0x84)
    load r3, -1
    store [0x84], r3
    jmp end_if_1
;else {
else1:
    ;if (digit == 1){
    cmp r0, 1
    jne else2

    ;print_word(0, 0x84)
    load r3, 0
    store [0x84], r3
    jmp end_if_2

else2:

    ;let flag = 0
    load r1, 0
    store [flag], r1

    ;let i = 2
    load r2, 2
    store [i], r2

    ;while(i*i<= digit){
loop1:
    mul r4, r2, r2
    cmp r4, r0
    jgt end_loop1

    ;if(digit%i == 0){
    mod r3, r0, r2
    cmp r3, 0
    jne end_if_3
    load r3, 1 
    store [flag], r3
    load r1, 1         
    jmp end_loop1
end_if_3:
    load r2, [i]
    add r2, r2, 1
    store [i], r2
    jmp loop1

end_loop1:
    cmp r1, 1
    jne else4
    load r3, 0
    store [0x84], r3
    jmp end_if_4
else4:
    load r3, 1 
    store [0x84], r3

end_if_4:
end_if_2:
end_if_1:
end:
    halt
