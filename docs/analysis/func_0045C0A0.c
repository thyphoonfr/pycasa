// Address: 0045c0a0
// Function: FUN_0045c0a0
// Target requested: 0x0045C0A0

/* WARNING: Removing unreachable block (ram,0x0045c1ea) */
/* WARNING: Removing unreachable block (ram,0x0045c1f5) */
/* WARNING: Removing unreachable block (ram,0x0045c204) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void __thiscall FUN_0045c0a0(int param_1,undefined4 param_2,char *param_3)

{
  char cVar1;
  int iVar2;
  char *pcVar3;
  char *pcVar4;
  int unaff_EBX;
  byte *unaff_ESI;
  byte *pbVar5;
  undefined *apuStack_a64 [2];
  char acStack_a5c [12];
  undefined4 uStack_a50;
  char *pcStack_a4c;
  int iStack_a48;
  char *pcStack_a40;
  undefined4 uStack_a3c;
  uint uStack_c;
  
  uStack_c = _DAT_00d24004 ^ (uint)apuStack_a64;
  uStack_a3c = param_2;
  pcStack_a40 = param_3;
  FUN_00410610(acStack_a5c,&UNK_00c80a6c);
  apuStack_a64[0] = &UNK_00c81f14;
  uStack_a50 = 0;
  pcStack_a4c = (char *)0x0;
  (**(code **)(*(int *)(param_1 + 0x48) + 0xf0))(apuStack_a64);
  if ((_DAT_00d6769c == 0) || (iVar2 = func_0x005a9b40(apuStack_a64), iVar2 != 1000000)) {
    if (acStack_a5c[0] == -1) {
      func_0x00998e70(1);
      if (acStack_a5c[0] != '\0') goto LAB_0045c121;
      acStack_a5c[0] = -1;
      func_0x004089e0(apuStack_a64);
      func_0x009a37b0();
      if (iStack_a48 == 0) {
        pcVar4 = (char *)0x0;
      }
      else {
        pcVar4 = (char *)(iStack_a48 + 4);
      }
      pcVar3 = pcVar4;
      if (pcVar4 != (char *)0x0) {
        do {
          cVar1 = *pcVar3;
          pcVar3 = pcVar3 + 1;
        } while (cVar1 != '\0');
        func_0x00985ff0(pcVar4);
      }
      if (unaff_EBX != 0) {
        func_0x00401000();
      }
      func_0x00401000();
      func_0x00998e70(1);
      if ((char)apuStack_a64[0] != '\x01') {
        func_0x009a37b0();
        if (pcStack_a4c == (char *)0x0) {
          pcVar4 = (char *)0x0;
        }
        else {
          pcVar4 = pcStack_a4c + 4;
        }
        pbVar5 = (byte *)0x0;
        pcVar3 = pcVar4;
        if (pcVar4 != (char *)0x0) {
          do {
            cVar1 = *pcVar3;
            pcVar3 = pcVar3 + 1;
          } while (cVar1 != '\0');
          pbVar5 = (byte *)0x0;
          func_0x00985ff0(pcVar4);
        }
        if (((unaff_ESI != pbVar5) && (func_0x00401000(), pbVar5 != (byte *)0x0)) &&
           ((0x7f < *pbVar5 || (cVar1 = InterlockedIncrement(pbVar5), cVar1 == -1)))) {
          func_0x00985a60();
        }
        func_0x00401000();
      }
      func_0x00408c00();
      param_3 = pcStack_a4c;
    }
    if ((acStack_a5c[0] == '\0') && ((param_3 == (char *)0x0 || (*param_3 == '\0')))) {
      func_0x00410770();
      func_0x00bef10a();
      return;
    }
  }
  else {
    acStack_a5c[0] = '\x01';
  }
LAB_0045c121:
  func_0x005ab210(&UNK_00c7f0fc,iStack_a48,param_3);
  func_0x00410770();
  func_0x00bef10a();
  return;
}


