// Address: 00410610
// Function: FUN_00410610
// Target requested: 0x00410610

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void __fastcall FUN_00410610(undefined1 param_1,char *param_2,undefined4 *param_3,int param_4)

{
  byte *pbVar1;
  char cVar2;
  char *pcVar3;
  char *pcVar4;
  undefined1 auStack_a44 [4];
  byte *pbStack_a40;
  int iStack_a3c;
  int iStack_a38;
  uint uStack_c;
  
  uStack_c = _DAT_00d24004 ^ (uint)auStack_a44;
  *param_3 = &UNK_00c81f04;
  param_3[1] = 0;
  param_3[2] = 0;
  *(undefined1 *)(param_3 + 3) = 0xff;
  *(undefined1 *)((int)param_3 + 0xd) = param_1;
  *(undefined1 *)((int)param_3 + 0xe) = 0;
  iStack_a3c = param_4;
  param_3[4] = 0;
  if (param_2 != (char *)0x0) {
    if (param_4 == 0) {
      pbStack_a40 = (byte *)0x0;
      pcVar4 = param_2;
      do {
        cVar2 = *pcVar4;
        pcVar4 = pcVar4 + 1;
      } while (cVar2 != '\0');
      func_0x00985ff0(param_2);
      func_0x005c2100();
      func_0x00401000();
    }
    else {
      func_0x00408b50();
      func_0x0049ff10();
      func_0x005c2100();
      func_0x00401000();
      func_0x009a37b0();
      if (iStack_a38 == 0) {
        pcVar4 = (char *)0x0;
      }
      else {
        pcVar4 = (char *)(iStack_a38 + 4);
      }
      pbStack_a40 = (byte *)0x0;
      pcVar3 = pcVar4;
      if (pcVar4 != (char *)0x0) {
        do {
          cVar2 = *pcVar3;
          pcVar3 = pcVar3 + 1;
        } while (cVar2 != '\0');
        func_0x00985ff0(pcVar4);
      }
      pbVar1 = pbStack_a40;
      if ((byte *)param_3[1] != pbStack_a40) {
        func_0x00401000();
        param_3[1] = pbVar1;
        if ((pbVar1 != (byte *)0x0) &&
           ((0x7f < *pbVar1 || (cVar2 = InterlockedIncrement(pbVar1), cVar2 == -1)))) {
          func_0x00985a60();
        }
      }
      func_0x00401000();
      func_0x00408c00();
    }
  }
  func_0x00bef10a();
  return;
}


