// [Input] Another live invocation's guest PID as argv[1].
// [Output] Exit zero after self, foreign and invalid tkill/tgkill checks.
// [Pos] Linux arm64 qualification probe, interpreted without host execution.
.text
.p2align 2
.globl _ink_guest_signal_fixture
_ink_guest_signal_fixture:
    ldr x0, [sp]
    cmp x0, #2
    b.ne 9f
    ldr x1, [sp, #16]
    mov x19, #0
1:
    ldrb w2, [x1], #1
    cbz w2, 2f
    sub w2, w2, #48
    cmp w2, #9
    b.hi 9f
    mov x3, #10
    madd x19, x19, x3, x2
    cmp x19, #32768
    b.hs 9f
    b 1b
2:
    cmp x19, #2
    b.lo 9f
    mov x8, #172
    svc #0
    mov x20, x0
    mov x1, #0
    mov x8, #130
    svc #0
    cbnz x0, 9f
    mov x0, x20
    mov x1, x20
    mov x2, #0
    mov x8, #131
    svc #0
    cbnz x0, 9f
    mov x0, x19
    mov x1, #0
    mov x8, #130
    svc #0
    cmn x0, #1
    b.ne 9f
    mov x0, x19
    mov x1, x19
    mov x2, #0
    mov x8, #131
    svc #0
    cmn x0, #1
    b.ne 9f
    mov x0, x20
    mov x1, x19
    mov x2, #0
    mov x8, #131
    svc #0
    cmn x0, #3
    b.ne 9f
    mov x0, #0
    mov x1, #0
    mov x8, #130
    svc #0
    cmn x0, #22
    b.ne 9f
    mov x0, #0
    mov x1, x20
    mov x2, #0
    mov x8, #131
    svc #0
    cmn x0, #22
    b.ne 9f
    mov x0, #0
    b 10f
9:
    mov x0, #91
10:
    mov x8, #93
    svc #0
    brk #0
