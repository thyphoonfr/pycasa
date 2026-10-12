// Address: 005aa260
// Function: FUN_005aa260
// Target requested: 0x005AA260

/* WARNING: Removing unreachable block (ram,0x005aa2c0) */
/* WARNING: Removing unreachable block (ram,0x005aa2d8) */
/* WARNING: Removing unreachable block (ram,0x005aa2eb) */
/* WARNING: Removing unreachable block (ram,0x005aa2f4) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 __thiscall FUN_005aa260(char *param_1,int param_2,char *param_3,char *param_4)

{
  byte *pbVar1;
  undefined4 uVar2;
  char cVar3;
  uint *puVar4;
  char *pcVar5;
  uint uVar6;
  uint uVar7;
  uint *puVar8;
  uint *puVar9;
  int iVar10;
  uint uVar11;
  uint uVar12;
  undefined4 uStack_24;
  undefined4 uStack_20;
  uint *puStack_1c;
  uint uStack_18;
  uint *puStack_14;
  uint uStack_10;
  byte *pbStack_c;
  undefined4 uStack_8;
  undefined4 uStack_4;
  
  uVar2 = _DAT_00d6769c;
  puVar8 = (uint *)0x0;
  uStack_20 = 0;
  puStack_1c = (uint *)0x0;
  uStack_18 = 0;
  puStack_14 = (uint *)0x0;
  uStack_10 = 0;
  pbStack_c = (byte *)0x0;
  uStack_24 = 1;
  pcVar5 = param_1;
  if (param_1 != (char *)0x0) {
    do {
      cVar3 = *pcVar5;
      pcVar5 = pcVar5 + 1;
    } while (cVar3 != '\0');
    func_0x00985ff0(param_1);
  }
  func_0x00401000();
  pcVar5 = param_3;
  if (param_3 != (char *)0x0) {
    do {
      cVar3 = *pcVar5;
      pcVar5 = pcVar5 + 1;
    } while (cVar3 != '\0');
    func_0x00985ff0(param_3);
  }
  if ((uStack_18 & 1) == 0) {
    uVar11 = uStack_18 >> 1;
    if (uVar11 * 4 < 0x100000) {
      uVar12 = uVar11;
      if ((uVar11 & uVar11 - 1) == 0) {
        if (uVar11 == 0) {
          uVar12 = 1;
        }
        else {
          uVar12 = uVar11 * 2;
        }
      }
    }
    else {
      uVar12 = (uVar11 & 0x7ffffc00) + 0x400;
    }
    puVar4 = puStack_1c;
    if (uVar11 < uVar12) {
      puVar9 = puVar8;
      puVar8 = (uint *)0x0;
      if (uVar12 == 0) {
LAB_005aa429:
        puVar4 = puVar8;
        if (puVar9 != (uint *)0x0) {
          func_0x00401110(4,&UNK_005bd380);
          func_0x0097caf0(puVar9 + -1);
        }
      }
      else {
        uVar6 = -(uint)((int)((ulonglong)uVar12 * 4 >> 0x20) != 0) | (uint)((ulonglong)uVar12 * 4);
        puVar4 = (uint *)func_0x0097c5d0(-(uint)(0xfffffffb < uVar6) | uVar6 + 4);
        if (puVar4 != (uint *)0x0) {
          puVar8 = puVar4 + 1;
          *puVar4 = uVar12;
          func_0x004010e0(4,&UNK_00412780);
          if (puVar8 != (uint *)0x0) {
            if (uVar11 <= uVar12) {
              uVar12 = uVar11;
            }
            if (uVar12 != 0) {
              puVar4 = puVar8;
              do {
                if (*puVar4 != *(uint *)(-(int)puVar8 + (int)puVar4)) {
                  func_0x00401000();
                  pbVar1 = *(byte **)(-(int)puVar8 + (int)puVar4);
                  *puVar4 = (uint)pbVar1;
                  if ((pbVar1 != (byte *)0x0) &&
                     ((0x7f < *pbVar1 || (cVar3 = InterlockedIncrement(pbVar1), cVar3 == -1)))) {
                    func_0x00985a60();
                  }
                }
                puVar4 = puVar4 + 1;
                uVar12 = uVar12 - 1;
                puVar9 = puStack_1c;
              } while (uVar12 != 0);
            }
            goto LAB_005aa429;
          }
        }
        puVar8 = (uint *)0x0;
        puVar4 = puStack_1c;
      }
    }
    puStack_1c = puVar4;
    if (puVar8 != (uint *)0x0) {
      func_0x005c2100();
      uStack_18 = (uStack_18 & 0xfffffffe) + 2;
    }
  }
  func_0x00401000();
  pcVar5 = param_4;
  if (param_4 != (char *)0x0) {
    do {
      cVar3 = *pcVar5;
      pcVar5 = pcVar5 + 1;
    } while (cVar3 != '\0');
    func_0x00985ff0(param_4);
  }
  uVar11 = uStack_10;
  if ((uStack_10 & 1) != 0) goto LAB_005aa5fd;
  uVar12 = uStack_10 >> 1;
  if (uVar12 * 4 < 0x100000) {
    uVar6 = uVar12;
    if ((uVar12 & uVar12 - 1) == 0) {
      if (uVar12 == 0) {
        uVar6 = 1;
      }
      else {
        uVar6 = uVar12 * 2;
      }
    }
  }
  else {
    uVar6 = (uVar12 & 0x7ffffc00) + 0x400;
  }
  puVar8 = puStack_14;
  puVar4 = puStack_14;
  if (uVar12 < uVar6) {
    puVar8 = (uint *)0x0;
    if (uVar6 == 0) {
LAB_005aa5ac:
      puVar4 = puVar8;
      if (puStack_14 != (uint *)0x0) {
        puVar9 = puStack_14 + -1;
        func_0x00401110(4,&UNK_005bd380);
        func_0x0097caf0(puVar9);
      }
    }
    else {
      uVar7 = -(uint)((int)((ulonglong)uVar6 * 4 >> 0x20) != 0) | (uint)((ulonglong)uVar6 * 4);
      puVar4 = (uint *)func_0x0097c5d0(-(uint)(0xfffffffb < uVar7) | uVar7 + 4);
      if (puVar4 != (uint *)0x0) {
        puVar8 = puVar4 + 1;
        *puVar4 = uVar6;
        func_0x004010e0(4,&UNK_00412780);
        if (puVar8 != (uint *)0x0) {
          if (uVar12 <= uVar6) {
            uVar6 = uVar12;
          }
          if (uVar6 != 0) {
            iVar10 = (int)puStack_14 - (int)puVar8;
            puVar4 = puVar8;
            do {
              if (*puVar4 != *(uint *)(iVar10 + (int)puVar4)) {
                func_0x00401000();
                pbVar1 = *(byte **)(iVar10 + (int)puVar4);
                *puVar4 = (uint)pbVar1;
                if ((pbVar1 != (byte *)0x0) &&
                   ((0x7f < *pbVar1 || (cVar3 = InterlockedIncrement(pbVar1), cVar3 == -1)))) {
                  func_0x00985a60();
                }
              }
              puVar4 = puVar4 + 1;
              uVar6 = uVar6 - 1;
              uVar11 = uStack_10;
            } while (uVar6 != 0);
          }
          goto LAB_005aa5ac;
        }
      }
      puVar8 = (uint *)0x0;
      puVar4 = puStack_14;
    }
  }
  puStack_14 = puVar4;
  if (puVar8 != (uint *)0x0) {
    func_0x005c2100();
    uStack_10 = (uVar11 & 0xfffffffe) + 2;
  }
LAB_005aa5fd:
  func_0x00401000();
  if (pbStack_c != *(byte **)(param_2 + 4)) {
    func_0x00401000();
    pbStack_c = *(byte **)(param_2 + 4);
    if ((pbStack_c != (byte *)0x0) &&
       ((0x7f < *pbStack_c || (cVar3 = InterlockedIncrement(pbStack_c), cVar3 == -1)))) {
      func_0x00985a60();
    }
  }
  uStack_8 = *(undefined4 *)(param_2 + 0x14);
  uStack_4 = *(undefined4 *)(param_2 + 0x18);
  func_0x005a8d60(uVar2,&uStack_24);
  func_0x005aa6b0();
  return 0;
}


