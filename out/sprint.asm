; Sprint (Google CTF 2020) - disassembly da ISA implementada em sprintf
; PC/OUT = program counter / buffer de saida; r1.. = registradores
; valores sao mod 2^16 (escrita via %hn de 16 bits)
;
;   offset  kind  instrucao
;------------------------------------------------------------
0x000000  MOV   PC = 38; r3 = 28672
0x000026  ALU   PC = 74; r2 = r2
0x00004a  MOV   PC = 108; r1 = 1
0x00006c  ALU   PC = 149; r2 = r2 + 2
0x000095  MOV   PC = 183; r1 = 1
0x0000b7  MOV   PC = 218; r4 = 2
0x0000da  ALU   PC = 264; r7 = 2*r3
0x000108  ALU   PC = 310; r2 = r6 + 28672
0x000136  ALU   PC = 347; r6 = r1
0x00015b  BR    PC = OUT + 384
0x000180  ALU   PC = 430; r5 = 2*r3
0x0001ae  MOV   PC = 468; r2 = 65519
0x0001d4  ALU   PC = 505; r1 = r4
0x0001f9  MOV   PC = 543; r2 = 65520
0x00021f  ALU   PC = 580; r6 = r1
0x000244  BR    PC = OUT + 617
0x000269  ALU   PC = 663; r7 = 2*r4
0x000297  ALU   PC = 709; r2 = r6 + 28672
0x0002c5  MOV   PC = 743; r1 = 1
0x0002e7  ALU   PC = 789; r5 = r4 + r3
0x000315  JMP   PC = 430
0x000324  ALU   PC = 847; r4 = r3 + 1
0x00034f  BR    PC = OUT + 884
0x000374  MOV   PC = 922; r3 = 57344
0x00039a  MOV   PC = 957; r4 = 0
0x0003bd  ALU   PC = 993; r2 = r2
0x0003e1  ALU   PC = 1030; r5 = r1
0x000406  BR    PC = OUT + 1067
0x00042b  JMP   PC = 1185
0x00043a  ALU   PC = 1129; r4 = r3 + 65535
0x000469  ALU   PC = 1170; r3 = r2 + 1
0x000492  JMP   PC = 957
0x0004a1  ALU   PC = 1232; r7 = r3 + 254
0x0004d0  BR    PC = OUT + 1269
0x0004f5  JMP   PC = 1334
0x000504  MOV   PC = 1319; r10 = 5
0x000527  JMP   PC = 5081
0x000536  MOV   PC = 1368; r3 = 0
0x000558  MOV   PC = 1403; r4 = 0
0x00057b  MOV   PC = 1441; r2 = 61696
0x0005a1  ALU   PC = 1478; r5 = r1
0x0005c6  MOV   PC = 1513; r6 = 1
0x0005e9  MOV   PC = 1548; r10 = 0
0x00060c  ALU   PC = 1593; r2 = r2 + 57344
0x000639  ALU   PC = 1630; r7 = r1
0x00065e  BR    PC = OUT + 1667
0x000683  JMP   PC = 3479
0x000692  ALU   PC = 1723; r3 = r2 + 1
0x0006bb  ALU   PC = 1770; r8 = r6 + 65419
0x0006ea  BR    PC = OUT + 1807
0x00070f  MOV   PC = 1846; r7 = 65520
0x000736  JMP   PC = 2373
0x000745  ALU   PC = 1908; r8 = r6 + 65422
0x000774  BR    PC = OUT + 1945
0x000799  MOV   PC = 1980; r7 = 1
0x0007bc  JMP   PC = 2373
0x0007cb  ALU   PC = 2042; r8 = r6 + 65436
0x0007fa  BR    PC = OUT + 2079
0x00081f  MOV   PC = 2115; r7 = 16
0x000843  JMP   PC = 2373
0x000852  ALU   PC = 2177; r8 = r6 + 65428
0x000881  BR    PC = OUT + 2214
0x0008a6  MOV   PC = 2253; r7 = 65535
0x0008cd  JMP   PC = 2373
0x0008dc  MOV   PC = 2303; r6 = 0
0x0008ff  MOV   PC = 2338; r7 = 0
0x000922  MOV   PC = 2373; r10 = 1
0x000945  ALU   PC = 2419; r5 = r4 + r6
0x000973  MOV   PC = 2457; r2 = 65519
0x000999  ALU   PC = 2494; r1 = r4
0x0009be  MOV   PC = 2532; r2 = 65520
0x0009e4  ALU   PC = 2569; r7 = r1
0x000a09  BR    PC = OUT + 2606
0x000a2e  ALU   PC = 2652; r2 = r4 + 61440
0x000a5c  ALU   PC = 2689; r7 = r1
0x000a81  MOV   PC = 2727; r2 = 65519
0x000aa7  ALU   PC = 2764; r1 = r6
0x000acc  MOV   PC = 2802; r2 = 65520
0x000af2  MOV   PC = 2836; r1 = 0
0x000b14  MOV   PC = 2874; r2 = 65519
0x000b3a  ALU   PC = 2911; r7 = r1
0x000b5f  ALU   PC = 2957; r7 = 2*r6
0x000b8d  ALU   PC = 3003; r2 = r6 + 28672
0x000bbb  ALU   PC = 3040; r7 = r1
0x000be0  BR    PC = OUT + 3077
0x000c05  ALU   PC = 3120; r7 = r3 + 1
0x000c30  ALU   PC = 3166; r2 = r6 + 61698
0x000c5e  ALU   PC = 3203; r7 = r1
0x000c83  ALU   PC = 3249; r7 = r6 + r4
0x000cb1  BR    PC = OUT + 3286
0x000cd6  ALU   PC = 3329; r4 = r3 + 1
0x000d01  JMP   PC = 1548
0x000d10  MOV   PC = 3379; r6 = 0
0x000d33  MOV   PC = 3414; r10 = 2
0x000d56  JMP   PC = 1548
0x000d65  MOV   PC = 3464; r10 = 4
0x000d88  JMP   PC = 65534
0x000d97  BR    PC = OUT + 3516
0x000dbc  JMP   PC = 5081
0x000dcb  ALU   PC = 3578; r7 = r3 + 65527
0x000dfa  BR    PC = OUT + 3615
0x000e1f  JMP   PC = 3680
0x000e2e  MOV   PC = 3665; r10 = 3
0x000e51  JMP   PC = 5081
0x000e60  MOV   PC = 3714; r3 = 0
0x000e82  MOV   PC = 3749; r4 = 0
0x000ea5  ALU   PC = 3795; r5 = r2 + 65497
0x000ed3  BR    PC = OUT + 3832
0x000ef8  JMP   PC = 4987
0x000f07  MOV   PC = 3882; r6 = 4
0x000f2a  MOV   PC = 3917; r5 = 0
0x000f4d  ALU   PC = 3963; r5 = 2*r4
0x000f7b  ALU   PC = 4009; r5 = 2*r4
0x000fa9  ALU   PC = 4055; r2 = r3 + 57344
0x000fd7  ALU   PC = 4092; r7 = r1
0x000ffc  ALU   PC = 4139; r8 = r6 + 65419
0x00102b  BR    PC = OUT + 4176
0x001050  JMP   PC = 4632
0x00105f  ALU   PC = 4238; r8 = r6 + 65422
0x00108e  BR    PC = OUT + 4275
0x0010b3  ALU   PC = 4318; r5 = r4 + 1
0x0010de  JMP   PC = 4632
0x0010ed  ALU   PC = 4380; r8 = r6 + 65436
0x00111c  BR    PC = OUT + 4417
0x001141  ALU   PC = 4460; r5 = r4 + 2
0x00116c  JMP   PC = 4632
0x00117b  ALU   PC = 4522; r8 = r6 + 65428
0x0011aa  BR    PC = OUT + 4559
0x0011cf  ALU   PC = 4602; r5 = r4 + 3
0x0011fa  JMP   PC = 4632
0x001209  JMP   PC = 5081
0x001218  ALU   PC = 4675; r4 = r3 + 1
0x001243  ALU   PC = 4722; r6 = r5 + 65535
0x001272  BR    PC = OUT + 4759
0x001297  ALU   PC = 4804; r2 = r2 + 61708
0x0012c4  ALU   PC = 4841; r6 = r1
0x0012e9  ALU   PC = 4886; r2 = r2 + 59392
0x001316  ALU   PC = 4931; r1 = r5 + r4
0x001343  ALU   PC = 4972; r3 = r2 + 1
0x00136c  JMP   PC = 3749
0x00137b  ALU   PC = 5032; r2 = r2 + 59392
0x0013a8  MOV   PC = 5066; r1 = 0
0x0013ca  JMP   PC = 65534
0x0013d9  MOV   PC = 5119; r2 = 59392
0x0013ff  MOV   PC = 5153; r1 = 0
0x001421  JMP   PC = 65534
0x00f000  JMP   (nop)
0x00f102  JMP   (nop)
