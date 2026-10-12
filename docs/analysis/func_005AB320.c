// Address: 005ab320
// Function: FUN_005ab320
// Target requested: 0x005AB320

/* WARNING: Removing unreachable block (ram,0x005ab48c) */
/* WARNING: Removing unreachable block (ram,0x005ab496) */
/* WARNING: Removing unreachable block (ram,0x005ab4a9) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void __thiscall FUN_005ab320(int param_1,char param_2)

{
  byte *pbVar1;
  undefined4 *puVar2;
  char cVar3;
  int iVar4;
  char *pcVar5;
  char *pcVar6;
  byte *pbStack_a44;
  undefined4 *puStack_a40;
  int iStack_a3c;
  uint uStack_c;
  
  uStack_c = _DAT_00d24004 ^ (uint)&pbStack_a44;
  if (((param_2 == '\0') || (_DAT_00d6769c == 0)) ||
     (iVar4 = func_0x005a9b40(param_1 + 4), iVar4 != 1000000)) {
    if ((*(char *)(param_1 + 0xc) == -1) && (func_0x00998e70(1), *(char *)(param_1 + 0xc) == '\0'))
    {
      iStack_a3c = param_1 + 4;
      *(undefined1 *)(param_1 + 0xc) = 0xff;
      func_0x004089e0(iStack_a3c);
      func_0x009a37b0();
      if (iStack_a3c == 0) {
        pcVar6 = (char *)0x0;
      }
      else {
        pcVar6 = (char *)(iStack_a3c + 4);
      }
      pbStack_a44 = (byte *)0x0;
      pcVar5 = pcVar6;
      if (pcVar6 != (char *)0x0) {
        do {
          cVar3 = *pcVar5;
          pcVar5 = pcVar5 + 1;
        } while (cVar3 != '\0');
        func_0x00985ff0(pcVar6);
      }
      puVar2 = puStack_a40;
      pbVar1 = pbStack_a44;
      if ((byte *)*puStack_a40 != pbStack_a44) {
        func_0x00401000();
        *puVar2 = pbVar1;
        if ((pbVar1 != (byte *)0x0) &&
           ((0x7f < *pbVar1 || (cVar3 = InterlockedIncrement(pbVar1), cVar3 == -1)))) {
          func_0x00985a60();
        }
      }
      func_0x00401000();
      func_0x00998e70(1);
      if (*(char *)(param_1 + 0xc) != '\x01') {
        func_0x009a37b0();
        if (puStack_a40 == (undefined4 *)0x0) {
          pcVar6 = (char *)0x0;
        }
        else {
          pcVar6 = (char *)(puStack_a40 + 1);
        }
        pcVar5 = pcVar6;
        if (pcVar6 != (char *)0x0) {
          do {
            cVar3 = *pcVar5;
            pcVar5 = pcVar5 + 1;
          } while (cVar3 != '\0');
          func_0x00985ff0(pcVar6);
        }
        pbVar1 = pbStack_a44;
        if (*(int *)pbStack_a44 != 0) {
          func_0x00401000();
          pbVar1[0] = 0;
          pbVar1[1] = 0;
          pbVar1[2] = 0;
          pbVar1[3] = 0;
        }
        func_0x00401000();
      }
      func_0x00408c00();
    }
  }
  else {
    *(undefined1 *)(param_1 + 0xc) = 1;
  }
  func_0x00bef10a();
  return;
}


