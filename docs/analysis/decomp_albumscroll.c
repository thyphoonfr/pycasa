// Address: 005dec84
// Function: FUN_005dec84
// Target requested: 0x005DEC84

void __fastcall FUN_005dec84(undefined4 param_1,undefined4 param_2)

{
  byte *pbVar1;
  char cVar2;
  undefined1 uVar3;
  int unaff_EBX;
  char *pcVar4;
  undefined4 *puVar5;
  undefined4 *unaff_EBP;
  int unaff_ESI;
  undefined4 uStack_8;
  
  uVar3 = in((short)param_2);
  puVar5 = (undefined4 *)&stack0xfffffffc;
  cVar2 = '\x12';
  do {
    unaff_EBP = unaff_EBP + -1;
    puVar5 = puVar5 + -1;
    *puVar5 = *unaff_EBP;
    cVar2 = cVar2 + -1;
  } while ('\0' < cVar2);
  pcVar4 = (char *)CONCAT31((int3)((uint)(unaff_EBX + 1) >> 8),
                            (char)(unaff_EBX + 1) + (char)((uint)param_1 >> 8));
  pbVar1 = (byte *)(pcVar4 + -0x74efdb8c);
  *pbVar1 = *pbVar1 >> 6 | *pbVar1 << 2;
  (**(code **)(CONCAT22((short)((uint)param_2 >> 0x10),
                        CONCAT11((char)((uint)param_2 >> 8) + *pcVar4,(char)param_2)) + 0x7c))
            (uVar3);
  *(undefined1 *)(unaff_ESI + 0x174) = 1;
  func_0x009cd8a0();
  return;
}


