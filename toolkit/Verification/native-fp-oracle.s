.text
.globl _fp_flags
_fp_flags:
fcmp s0, s1
mrs x0, nzcv
ret
.globl _fp_conditional
_fp_conditional:
cmp w0, #0
fccmp s0, s1, #5, eq
mrs x0, nzcv
ret
.globl _sample_branch
_sample_branch:
.inst 0x1e212000
b.lt L_sample_taken
mov w0, #0
ret
L_sample_taken:
mov w0, #1
ret
.globl _fp_cond_0
_fp_cond_0:
fcmp s0,s1
cset w0,eq
ret
.globl _fp_cond_1
_fp_cond_1:
fcmp s0,s1
cset w0,ne
ret
.globl _fp_cond_2
_fp_cond_2:
fcmp s0,s1
cset w0,cs
ret
.globl _fp_cond_3
_fp_cond_3:
fcmp s0,s1
cset w0,cc
ret
.globl _fp_cond_4
_fp_cond_4:
fcmp s0,s1
cset w0,mi
ret
.globl _fp_cond_5
_fp_cond_5:
fcmp s0,s1
cset w0,pl
ret
.globl _fp_cond_6
_fp_cond_6:
fcmp s0,s1
cset w0,vs
ret
.globl _fp_cond_7
_fp_cond_7:
fcmp s0,s1
cset w0,vc
ret
.globl _fp_cond_8
_fp_cond_8:
fcmp s0,s1
cset w0,hi
ret
.globl _fp_cond_9
_fp_cond_9:
fcmp s0,s1
cset w0,ls
ret
.globl _fp_cond_10
_fp_cond_10:
fcmp s0,s1
cset w0,ge
ret
.globl _fp_cond_11
_fp_cond_11:
fcmp s0,s1
cset w0,lt
ret
.globl _fp_cond_12
_fp_cond_12:
fcmp s0,s1
cset w0,gt
ret
.globl _fp_cond_13
_fp_cond_13:
fcmp s0,s1
cset w0,le
ret
