// Address: 006b8ac0
// Function: FUN_006b8ac0
// Target requested: 0x006B8AC0

/* WARNING: Removing unreachable block (ram,0x006b8dbc) */
/* WARNING: Removing unreachable block (ram,0x006b8c3a) */
/* WARNING: Removing unreachable block (ram,0x006b8f3c) */

int FUN_006b8ac0(undefined4 param_1)

{
  int iVar1;
  uint uVar2;
  undefined4 uVar3;
  uint uVar4;
  uint uVar5;
  uint uVar6;
  uint unaff_EBX;
  int unaff_ESI;
  int aiStack_c [2];
  float fStack_4;
  
  if (0xff < *(uint *)(unaff_ESI + 0x74)) {
    return -1;
  }
  iVar1 = FUN_006b8640(param_1);
  if (iVar1 != 0) {
    return iVar1;
  }
  if ((*(uint *)(unaff_ESI + 0x80) >> 1 <= *(uint *)(unaff_ESI + 0x74)) ||
     (*(int *)(unaff_ESI + 0x7c) + *(uint *)(unaff_ESI + 0x74) * 0x14 == 0)) {
    return -1;
  }
  aiStack_c[0] = 0;
  aiStack_c[1] = 0;
  func_0x0099de40(aiStack_c);
  if (aiStack_c[0] != 0) {
    return -1;
  }
  if (unaff_EBX < 4) {
    unaff_EBX = 4;
  }
  *(uint *)(unaff_ESI + 0x70) = unaff_EBX;
  uVar2 = *(uint *)(unaff_ESI + 0x60) >> 1;
  uVar5 = *(uint *)(unaff_ESI + 0x68) >> 1;
  if (uVar5 <= uVar2) {
    uVar2 = uVar5;
  }
  uVar5 = *(uint *)(unaff_ESI + 0x58) >> 1;
  if (uVar2 <= uVar5) {
    uVar5 = uVar2;
  }
  uVar2 = *(uint *)(unaff_ESI + 0x68) >> 1;
  if (uVar5 < 0x20000000) {
    if (uVar5 == uVar2) {
      iVar1 = *(int *)(unaff_ESI + 100);
    }
    else if ((*(uint *)(unaff_ESI + 0x68) & 1) == 0) {
      if (uVar5 * 4 < 0x100000) {
        uVar4 = 1;
        if (uVar5 != 0) {
          do {
            uVar4 = uVar4 * 2;
          } while (uVar4 <= uVar5);
        }
      }
      else {
        uVar4 = (uVar5 & 0xfffffc00) + 0x400;
      }
      if (uVar2 * 4 < 0x100000) {
        uVar6 = uVar2;
        if (1 < uVar2) {
          fStack_4 = (float)uVar2;
          uVar6 = 1 << ((char)((uint)fStack_4 >> 0x17) + 0x81U & 0x1f);
          if (uVar6 < uVar2) {
            uVar6 = uVar6 * 2;
          }
        }
      }
      else {
        uVar6 = (uVar2 & 0x7ffffc00) + 0x400;
      }
      iVar1 = *(int *)(unaff_ESI + 100);
      if (uVar6 != uVar4) {
        if (uVar4 == 0) {
          if (iVar1 != 0) {
            func_0x0097caf0(iVar1);
            *(undefined4 *)(unaff_ESI + 100) = 0;
          }
        }
        else {
          uVar3 = func_0x0097c810(iVar1,uVar4 * 4);
          *(undefined4 *)(unaff_ESI + 100) = uVar3;
        }
        iVar1 = *(int *)(unaff_ESI + 100);
        if (iVar1 == 0) {
          *(uint *)(unaff_ESI + 0x68) = *(uint *)(unaff_ESI + 0x68) & 1;
          *(undefined4 *)(unaff_ESI + 100) = 0;
          goto LAB_006b8cdd;
        }
      }
      *(uint *)(unaff_ESI + 0x68) = *(uint *)(unaff_ESI + 0x68) & 1 | uVar5 * 2;
    }
    else {
      if (uVar5 == 0) {
        if (*(int *)(unaff_ESI + 100) != 0) {
          func_0x0097caf0(*(int *)(unaff_ESI + 100));
          *(undefined4 *)(unaff_ESI + 100) = 0;
        }
      }
      else {
        uVar3 = func_0x0097c810(*(undefined4 *)(unaff_ESI + 100),uVar5 * 4);
        *(undefined4 *)(unaff_ESI + 100) = uVar3;
      }
      iVar1 = *(int *)(unaff_ESI + 100);
      if (iVar1 == 0) {
        *(uint *)(unaff_ESI + 0x68) = *(uint *)(unaff_ESI + 0x68) & 1;
        *(undefined4 *)(unaff_ESI + 100) = 0;
        goto LAB_006b8cdd;
      }
      *(uint *)(unaff_ESI + 0x68) = *(uint *)(unaff_ESI + 0x68) & 1 | uVar5 * 2;
    }
    if (iVar1 != 0) {
      for (; uVar2 < uVar5; uVar2 = uVar2 + 1) {
        *(undefined4 *)(*(int *)(unaff_ESI + 100) + uVar2 * 4) = 0;
      }
    }
  }
  else {
    if (*(int *)(unaff_ESI + 100) != 0) {
      func_0x0097caf0(*(int *)(unaff_ESI + 100));
    }
    *(uint *)(unaff_ESI + 0x68) = *(uint *)(unaff_ESI + 0x68) & 1;
    *(undefined4 *)(unaff_ESI + 100) = 0;
  }
LAB_006b8cdd:
  uVar2 = *(uint *)(unaff_ESI + 0x60) >> 1;
  if (uVar5 < 0x20000000) {
    if (uVar5 == uVar2) {
      iVar1 = *(int *)(unaff_ESI + 0x5c);
    }
    else if ((*(uint *)(unaff_ESI + 0x60) & 1) == 0) {
      if (uVar5 * 4 < 0x100000) {
        uVar4 = 1;
        if (uVar5 != 0) {
          do {
            uVar4 = uVar4 * 2;
          } while (uVar4 <= uVar5);
        }
      }
      else {
        uVar4 = (uVar5 & 0xfffffc00) + 0x400;
      }
      if (uVar2 * 4 < 0x100000) {
        uVar6 = uVar2;
        if (1 < uVar2) {
          fStack_4 = (float)uVar2;
          uVar6 = 1 << ((char)((uint)fStack_4 >> 0x17) + 0x81U & 0x1f);
          if (uVar6 < uVar2) {
            uVar6 = uVar6 * 2;
          }
        }
      }
      else {
        uVar6 = (uVar2 & 0x7ffffc00) + 0x400;
      }
      iVar1 = *(int *)(unaff_ESI + 0x5c);
      if (uVar6 != uVar4) {
        if (uVar4 == 0) {
          if (iVar1 != 0) {
            func_0x0097caf0(iVar1);
            *(undefined4 *)(unaff_ESI + 0x5c) = 0;
          }
        }
        else {
          uVar3 = func_0x0097c810(iVar1,uVar4 * 4);
          *(undefined4 *)(unaff_ESI + 0x5c) = uVar3;
        }
        iVar1 = *(int *)(unaff_ESI + 0x5c);
        if (iVar1 == 0) {
          *(uint *)(unaff_ESI + 0x60) = *(uint *)(unaff_ESI + 0x60) & 1;
          *(undefined4 *)(unaff_ESI + 0x5c) = 0;
          goto LAB_006b8e5d;
        }
      }
      *(uint *)(unaff_ESI + 0x60) = *(uint *)(unaff_ESI + 0x60) & 1 | uVar5 * 2;
    }
    else {
      iVar1 = *(int *)(unaff_ESI + 0x5c);
      if (uVar5 == 0) {
        if (iVar1 != 0) {
          func_0x0097caf0(iVar1);
          *(undefined4 *)(unaff_ESI + 0x5c) = 0;
        }
      }
      else {
        uVar3 = func_0x0097c810(iVar1,uVar5 * 4);
        *(undefined4 *)(unaff_ESI + 0x5c) = uVar3;
      }
      iVar1 = *(int *)(unaff_ESI + 0x5c);
      if (iVar1 == 0) {
        *(uint *)(unaff_ESI + 0x60) = *(uint *)(unaff_ESI + 0x60) & 1;
        *(undefined4 *)(unaff_ESI + 0x5c) = 0;
        goto LAB_006b8e5d;
      }
      *(uint *)(unaff_ESI + 0x60) = *(uint *)(unaff_ESI + 0x60) & 1 | uVar5 * 2;
    }
    if (iVar1 != 0) {
      for (; uVar2 < uVar5; uVar2 = uVar2 + 1) {
        *(undefined4 *)(*(int *)(unaff_ESI + 0x5c) + uVar2 * 4) = 0;
      }
    }
  }
  else {
    if (*(int *)(unaff_ESI + 0x5c) != 0) {
      func_0x0097caf0(*(int *)(unaff_ESI + 0x5c));
    }
    *(uint *)(unaff_ESI + 0x60) = *(uint *)(unaff_ESI + 0x60) & 1;
    *(undefined4 *)(unaff_ESI + 0x5c) = 0;
  }
LAB_006b8e5d:
  uVar2 = *(uint *)(unaff_ESI + 0x58) >> 1;
  if (uVar5 < 0x20000000) {
    if (uVar5 == uVar2) {
      iVar1 = *(int *)(unaff_ESI + 0x54);
    }
    else if ((*(uint *)(unaff_ESI + 0x58) & 1) == 0) {
      if (uVar5 * 4 < 0x100000) {
        uVar4 = 1;
        if (uVar5 != 0) {
          do {
            uVar4 = uVar4 * 2;
          } while (uVar4 <= uVar5);
        }
      }
      else {
        uVar4 = (uVar5 & 0xfffffc00) + 0x400;
      }
      if (uVar2 * 4 < 0x100000) {
        uVar6 = uVar2;
        if (1 < uVar2) {
          fStack_4 = (float)uVar2;
          uVar6 = 1 << ((char)((uint)fStack_4 >> 0x17) + 0x81U & 0x1f);
          if (uVar6 < uVar2) {
            uVar6 = uVar6 * 2;
          }
        }
      }
      else {
        uVar6 = (uVar2 & 0x7ffffc00) + 0x400;
      }
      iVar1 = *(int *)(unaff_ESI + 0x54);
      if (uVar6 != uVar4) {
        if (uVar4 == 0) {
          if (iVar1 != 0) {
            func_0x0097caf0(iVar1);
            *(undefined4 *)(unaff_ESI + 0x54) = 0;
          }
        }
        else {
          uVar3 = func_0x0097c810(iVar1,uVar4 * 4);
          *(undefined4 *)(unaff_ESI + 0x54) = uVar3;
        }
        iVar1 = *(int *)(unaff_ESI + 0x54);
        if (iVar1 == 0) {
          *(uint *)(unaff_ESI + 0x58) = *(uint *)(unaff_ESI + 0x58) & 1;
          *(undefined4 *)(unaff_ESI + 0x54) = 0;
          goto LAB_006b8fdd;
        }
      }
      *(uint *)(unaff_ESI + 0x58) = uVar5 * 2 | *(uint *)(unaff_ESI + 0x58) & 1;
    }
    else {
      iVar1 = *(int *)(unaff_ESI + 0x54);
      if (uVar5 == 0) {
        if (iVar1 != 0) {
          func_0x0097caf0(iVar1);
          *(undefined4 *)(unaff_ESI + 0x54) = 0;
        }
      }
      else {
        uVar3 = func_0x0097c810(iVar1,uVar5 * 4);
        *(undefined4 *)(unaff_ESI + 0x54) = uVar3;
      }
      iVar1 = *(int *)(unaff_ESI + 0x54);
      if (iVar1 == 0) {
        *(uint *)(unaff_ESI + 0x58) = *(uint *)(unaff_ESI + 0x58) & 1;
        *(undefined4 *)(unaff_ESI + 0x54) = 0;
        goto LAB_006b8fdd;
      }
      *(uint *)(unaff_ESI + 0x58) = uVar5 * 2 | *(uint *)(unaff_ESI + 0x58) & 1;
    }
    if (iVar1 != 0) {
      for (; uVar2 < uVar5; uVar2 = uVar2 + 1) {
        *(undefined4 *)(*(int *)(unaff_ESI + 0x54) + uVar2 * 4) = 0;
      }
    }
  }
  else {
    if (*(int *)(unaff_ESI + 0x54) != 0) {
      func_0x0097caf0(*(int *)(unaff_ESI + 0x54));
    }
    *(uint *)(unaff_ESI + 0x58) = *(uint *)(unaff_ESI + 0x58) & 1;
    *(undefined4 *)(unaff_ESI + 0x54) = 0;
  }
LAB_006b8fdd:
  uVar2 = 0;
  if ((*(uint *)(unaff_ESI + 0x60) & 0xfffffffe) != 0) {
    do {
      uVar5 = *(uint *)(*(int *)(unaff_ESI + 100) + uVar2 * 4);
      if ((uVar5 >> 0x18 == *(uint *)(unaff_ESI + 0x74)) &&
         (*(uint *)(unaff_ESI + 0x70) <
          (uVar5 & 0xffffff) + *(int *)(*(int *)(unaff_ESI + 0x5c) + uVar2 * 4))) {
        *(undefined4 *)(*(int *)(unaff_ESI + 0x5c) + uVar2 * 4) = 0;
        *(undefined4 *)(*(int *)(unaff_ESI + 100) + uVar2 * 4) = 0;
        *(undefined4 *)(*(int *)(unaff_ESI + 0x54) + uVar2 * 4) = 0;
      }
      uVar2 = uVar2 + 1;
    } while (uVar2 < *(uint *)(unaff_ESI + 0x60) >> 1);
  }
  return 0;
}


