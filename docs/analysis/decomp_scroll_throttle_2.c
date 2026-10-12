// Address: 00730320
// Function: FUN_00730320
// Target requested: 0x00730320

/* WARNING: Removing unreachable block (ram,0x007305c6) */

undefined4 __thiscall FUN_00730320(int param_1,int *param_2,uint param_3)

{
  uint uVar1;
  int *piVar2;
  int *piVar3;
  undefined4 *puVar4;
  uint uVar5;
  int iVar6;
  undefined4 *puVar7;
  uint uVar8;
  int iVar9;
  int iStack_30;
  uint uStack_2c;
  uint uStack_28;
  undefined4 *puStack_20;
  uint uStack_1c;
  int iStack_14;
  int iStack_c;
  
  uVar1 = *(uint *)(param_1 + 0x28c) >> 1;
  if (uVar1 == 0) {
    return 0;
  }
  puStack_20 = (undefined4 *)0x0;
  uStack_1c = 0;
  uStack_2c = param_3;
  if (param_3 < (uint)param_2[1] >> 1) {
    do {
      uStack_28 = 0;
      if (uVar1 != 0) {
        iStack_30 = 0;
        do {
          piVar2 = (int *)(*param_2 + uStack_2c * 0x10);
          piVar3 = (int *)(*(int *)(param_1 + 0x288) + iStack_30);
          iVar6 = *piVar2;
          if (*piVar2 < *piVar3) {
            iVar6 = *piVar3;
          }
          iStack_14 = piVar2[1];
          if (piVar2[1] < piVar3[1]) {
            iStack_14 = piVar3[1];
          }
          iVar9 = piVar2[2];
          if (piVar3[2] < piVar2[2]) {
            iVar9 = piVar3[2];
          }
          iStack_c = piVar2[3];
          if (piVar3[3] < piVar2[3]) {
            iStack_c = piVar3[3];
          }
          if ((iVar6 < iVar9) && (iStack_14 < iStack_c)) {
            uVar1 = uStack_1c >> 1;
            if (uVar1 * 0x10 < 0x100000) {
              uVar5 = uVar1;
              if ((uVar1 & uVar1 - 1) == 0) {
                if (uVar1 == 0) {
                  uVar5 = 1;
                }
                else {
                  uVar5 = uVar1 * 2;
                }
              }
            }
            else {
              uVar5 = (uVar1 & 0x7ffffc00) + 0x400;
            }
            if (uVar1 < uVar5) {
              if (uVar5 == 0) {
                if (puStack_20 != (undefined4 *)0x0) {
                  func_0x0097caf0(puStack_20);
                  puStack_20 = (undefined4 *)0x0;
                }
                goto LAB_0073048b;
              }
              puStack_20 = (undefined4 *)func_0x0097c810(puStack_20,uVar5 << 4);
            }
            if (puStack_20 != (undefined4 *)0x0) {
              puStack_20[uVar1 * 4] = iVar6;
              puStack_20[uVar1 * 4 + 1] = iStack_14;
              puStack_20[uVar1 * 4 + 2] = iVar9;
              uStack_1c = uStack_1c + 2;
              puStack_20[uVar1 * 4 + 3] = iStack_c;
            }
          }
LAB_0073048b:
          iStack_30 = iStack_30 + 0x10;
          uStack_28 = uStack_28 + 1;
          uVar1 = *(uint *)(param_1 + 0x28c) >> 1;
        } while (uStack_28 < uVar1);
      }
      uStack_2c = uStack_2c + 1;
    } while (uStack_2c < (uint)param_2[1] >> 1);
  }
  uVar1 = (uint)param_2[1] >> 1;
  if (param_3 < 0x8000000) {
    if (param_3 == uVar1) {
      iVar6 = *param_2;
    }
    else if ((param_2[1] & 1U) == 0) {
      if (param_3 << 4 < 0x100000) {
        uVar5 = 1;
        if (param_3 != 0) {
          do {
            uVar5 = uVar5 * 2;
          } while (uVar5 <= param_3);
        }
      }
      else {
        uVar5 = (param_3 & 0xfffffc00) + 0x400;
      }
      if (uVar1 << 4 < 0x100000) {
        uVar8 = uVar1;
        if ((1 < uVar1) &&
           (uVar8 = 1 << ((char)((uint)(float)uVar1 >> 0x17) + 0x81U & 0x1f), uVar8 < uVar1)) {
          uVar8 = uVar8 * 2;
        }
      }
      else {
        uVar8 = (uVar1 & 0x7ffffc00) + 0x400;
      }
      iVar6 = *param_2;
      if (uVar8 != uVar5) {
        if (uVar5 == 0) {
          if (iVar6 != 0) {
            func_0x0097caf0(iVar6);
            *param_2 = 0;
          }
        }
        else {
          iVar6 = func_0x0097c810(iVar6,uVar5 << 4);
          *param_2 = iVar6;
        }
        iVar6 = *param_2;
        if (iVar6 == 0) {
          param_2[1] = param_2[1] & 1;
          *param_2 = 0;
          goto LAB_00730679;
        }
      }
      param_2[1] = param_2[1] & 1U | param_3 * 2;
    }
    else {
      if (param_3 == 0) {
        if (*param_2 != 0) {
          func_0x0097caf0(*param_2);
          *param_2 = 0;
        }
      }
      else {
        iVar6 = func_0x0097c810(*param_2,param_3 << 4);
        *param_2 = iVar6;
      }
      iVar6 = *param_2;
      if (iVar6 == 0) {
        param_2[1] = param_2[1] & 1;
        *param_2 = 0;
        goto LAB_00730679;
      }
      param_2[1] = param_2[1] & 1U | param_3 * 2;
    }
    if ((iVar6 != 0) && (uVar1 < param_3)) {
      iVar6 = uVar1 << 4;
      iVar9 = param_3 - uVar1;
      do {
        puVar4 = (undefined4 *)(*param_2 + iVar6);
        *puVar4 = 0;
        puVar4[1] = 0;
        iVar6 = iVar6 + 0x10;
        iVar9 = iVar9 + -1;
        puVar4[2] = 0;
        puVar4[3] = 0;
      } while (iVar9 != 0);
    }
  }
  else {
    if (*param_2 != 0) {
      func_0x0097caf0(*param_2);
    }
    param_2[1] = param_2[1] & 1;
    *param_2 = 0;
  }
LAB_00730679:
  puVar4 = puStack_20;
  for (uStack_1c = uStack_1c >> 1; uStack_1c != 0; uStack_1c = uStack_1c - 1) {
    if ((param_2[1] & 1U) == 0) {
      uVar1 = (uint)param_2[1] >> 1;
      if (uVar1 << 4 < 0x100000) {
        uVar5 = uVar1;
        if ((uVar1 & uVar1 - 1) == 0) {
          if (uVar1 == 0) {
            uVar5 = 1;
          }
          else {
            uVar5 = uVar1 * 2;
          }
        }
      }
      else {
        uVar5 = (uVar1 & 0x7ffffc00) + 0x400;
      }
      if (uVar1 < uVar5) {
        if (uVar5 == 0) {
          if (*param_2 != 0) {
            func_0x0097caf0(*param_2);
            *param_2 = 0;
          }
        }
        else {
          iVar6 = func_0x0097c810(*param_2,uVar5 << 4);
          *param_2 = iVar6;
        }
      }
      if (*param_2 != 0) {
        puVar7 = (undefined4 *)(((uint)param_2[1] >> 1) * 0x10 + *param_2);
        *puVar7 = *puVar4;
        puVar7[1] = puVar4[1];
        puVar7[2] = puVar4[2];
        puVar7[3] = puVar4[3];
        param_2[1] = (param_2[1] & 0xfffffffeU) + 2 ^ param_2[1] & 1U;
      }
    }
    puVar4 = puVar4 + 4;
  }
  if (*(int *)(param_1 + 0x288) != 0) {
    func_0x0097caf0(*(int *)(param_1 + 0x288));
  }
  *(uint *)(param_1 + 0x28c) = *(uint *)(param_1 + 0x28c) & 1;
  *(undefined4 *)(param_1 + 0x288) = 0;
  if (puStack_20 != (undefined4 *)0x0) {
    func_0x0097caf0(puStack_20);
  }
  return 0;
}


