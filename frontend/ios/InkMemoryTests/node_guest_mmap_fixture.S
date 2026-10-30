// [Input] Qualification file and a one-byte stdin handshake after host-side rename.
// [Output] Exit zero only when shared writable mmap returns Linux EACCES.
// [Pos] Linux arm64 syscall probe, interpreted inside the existing guest core.
.text
.p2align 2
.globl _ink_guest_mmap_fixture
_ink_guest_mmap_fixture:
    mov x0, #-100
    adr x1, 1f
    mov x2, #2
    mov x3, #0
    mov x8, #56
    svc #0
    tbnz x0, #63, 5f
    mov x19, x0
    mov x0, #1
    adr x1, 2f
    mov x2, #5
    mov x8, #64
    svc #0
    mov x0, #0
    adr x1, 3f
    mov x2, #1
    mov x8, #63
    svc #0
    cmp x0, #1
    b.ne 5f
    mov x0, #0
    mov x1, #4096
    mov x2, #3
    mov x3, #1
    mov x4, x19
    mov x5, #0
    mov x8, #222
    svc #0
    cmn x0, #13
    b.ne 5f
    mov x0, #0
    b 6f
5:
    mov x0, #91
6:
    mov x8, #93
    svc #0
    brk #0
1:
    .asciz "/workspace/mmap-moved.txt"
2:
    .ascii "ready"
3:
    .byte 0
