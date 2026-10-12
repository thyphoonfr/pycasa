// Address: 006b75f0
// Function: FUN_006b75f0
// Target requested: 0x006B75F0

/* WARNING: Removing unreachable block (ram,0x006b7959) */
/* WARNING: Removing unreachable block (ram,0x006b77a9) */
/* WARNING: Removing unreachable block (ram,0x006b7ad6) */

int __thiscall FUN_006b75f0(int *param_1,uint param_2,uint *param_3,undefined4 param_4)

{
  uint *puVar1;
  bool bVar2;
  undefined4 uVar3;
  int iVar4;
  int iVar5;
  byte *pbVar6;
  uint uVar7;
  uint uVar8;
  byte *pbVar9;
  uint uVar10;
  uint uVar11;
  int unaff_retaddr;
  
  if (0xffffff < *param_3) {
    return -1;
  }
  iVar4 = GetCurrentThreadId();
  if ((param_1[8] == 0) || (param_1[8] != iVar4)) {
    if ((char)param_1[3] == '\0') {
      (**(code **)(*param_1 + 0x18))();
    }
    else {
      EnterCriticalSection(param_1 + 10);
    }
    param_1[9] = 0;
    param_1[8] = iVar4;
  }
  else {
    param_1[9] = param_1[9] + 1;
  }
  param_1[0x13] = param_1[0x13] + 1;
  *(undefined1 *)(param_1 + 0x14) = 1;
  if ((param_2 & 0xfffffffe) == param_1[0x23]) {
    param_1[0x23] = -1;
    if ((param_1[0x24] != 0) && (param_1[0x25] != 0)) {
      func_0x0097caf0(param_1[0x25]);
    }
    param_1[0x24] = 0;
    param_1[0x25] = 0;
  }
  if ((uint)param_1[0x1a] >> 1 <= param_2) {
    uVar11 = param_2 + 1;
    uVar10 = (uint)param_1[0x18] >> 1;
    if (0x1fffffff < uVar11) {
      if (param_1[0x17] != 0) {
        func_0x0097caf0(param_1[0x17]);
      }
LAB_006b76bf:
      param_1[0x18] = param_1[0x18] & 1;
      param_1[0x17] = 0;
      goto LAB_006b76c6;
    }
    if (uVar11 == uVar10) {
      iVar4 = param_1[0x17];
    }
    else if ((param_1[0x18] & 1U) == 0) {
      if (uVar11 * 4 < 0x100000) {
        uVar7 = 1;
        if (uVar11 != 0) {
          do {
            uVar7 = uVar7 * 2;
          } while (uVar7 <= uVar11);
        }
      }
      else {
        uVar7 = (uVar11 & 0xfffffc00) + 0x400;
      }
      if (uVar10 * 4 < 0x100000) {
        uVar8 = uVar10;
        if ((1 < uVar10) &&
           (uVar8 = 1 << ((char)((uint)(float)uVar10 >> 0x17) + 0x81U & 0x1f), uVar8 < uVar10)) {
          uVar8 = uVar8 * 2;
        }
      }
      else {
        uVar8 = (uVar10 & 0x7ffffc00) + 0x400;
      }
      iVar4 = param_1[0x17];
      if (uVar8 != uVar7) {
        if (uVar7 == 0) {
          if (iVar4 != 0) {
            func_0x0097caf0(iVar4);
            param_1[0x17] = 0;
          }
        }
        else {
          iVar4 = func_0x0097c810(iVar4,uVar7 * 4);
          param_1[0x17] = iVar4;
        }
        iVar4 = param_1[0x17];
        if (iVar4 == 0) goto LAB_006b76bf;
      }
      param_1[0x18] = param_1[0x18] & 1U | uVar11 * 2;
    }
    else {
      if (uVar11 == 0) {
        if (param_1[0x17] != 0) {
          func_0x0097caf0(param_1[0x17]);
          param_1[0x17] = 0;
        }
      }
      else {
        iVar4 = func_0x0097c810(param_1[0x17],uVar11 * 4);
        param_1[0x17] = iVar4;
      }
      iVar4 = param_1[0x17];
      if (iVar4 == 0) goto LAB_006b76bf;
      param_1[0x18] = param_1[0x18] & 1U | uVar11 * 2;
    }
    if (iVar4 == 0) goto LAB_006b76c6;
    for (; uVar10 < uVar11; uVar10 = uVar10 + 1) {
      *(undefined4 *)(param_1[0x17] + uVar10 * 4) = 0;
    }
    uVar10 = (uint)param_1[0x16] >> 1;
    if (0x1fffffff < uVar11) {
      if (param_1[0x15] != 0) {
        func_0x0097caf0(param_1[0x15]);
        param_1[0x16] = param_1[0x16] & 1;
        param_1[0x15] = 0;
        goto LAB_006b76c6;
      }
LAB_006b79bd:
      param_1[0x16] = param_1[0x16] & 1;
      param_1[0x15] = 0;
      goto LAB_006b76c6;
    }
    if (uVar11 == uVar10) {
      iVar4 = param_1[0x15];
    }
    else if ((param_1[0x16] & 1U) == 0) {
      if (uVar11 * 4 < 0x100000) {
        uVar7 = 1;
        if (uVar11 != 0) {
          do {
            uVar7 = uVar7 * 2;
          } while (uVar7 <= uVar11);
        }
      }
      else {
        uVar7 = (uVar11 & 0xfffffc00) + 0x400;
      }
      if (uVar10 * 4 < 0x100000) {
        uVar8 = uVar10;
        if ((1 < uVar10) &&
           (uVar8 = 1 << ((char)((uint)(float)uVar10 >> 0x17) + 0x81U & 0x1f), uVar8 < uVar10)) {
          uVar8 = uVar8 * 2;
        }
      }
      else {
        uVar8 = (uVar10 & 0x7ffffc00) + 0x400;
      }
      iVar4 = param_1[0x15];
      if (uVar8 != uVar7) {
        if (uVar7 == 0) {
          if (iVar4 != 0) {
            func_0x0097caf0(iVar4);
            param_1[0x15] = 0;
          }
        }
        else {
          iVar4 = func_0x0097c810(iVar4,uVar7 * 4);
          param_1[0x15] = iVar4;
        }
        iVar4 = param_1[0x15];
        if (iVar4 == 0) goto LAB_006b79bd;
      }
      param_1[0x16] = param_1[0x16] & 1U | uVar11 * 2;
    }
    else {
      if (uVar11 == 0) {
        if (param_1[0x15] != 0) {
          func_0x0097caf0(param_1[0x15]);
          param_1[0x15] = 0;
        }
      }
      else {
        iVar4 = func_0x0097c810(param_1[0x15],uVar11 * 4);
        param_1[0x15] = iVar4;
      }
      iVar4 = param_1[0x15];
      if (iVar4 == 0) goto LAB_006b79bd;
      param_1[0x16] = param_1[0x16] & 1U | uVar11 * 2;
    }
    if (iVar4 == 0) goto LAB_006b76c6;
    for (; uVar10 < uVar11; uVar10 = uVar10 + 1) {
      *(undefined4 *)(param_1[0x15] + uVar10 * 4) = 0;
    }
    uVar10 = (uint)param_1[0x1a] >> 1;
    if (0x1fffffff < uVar11) {
      if (param_1[0x19] != 0) {
        func_0x0097caf0(param_1[0x19]);
        param_1[0x1a] = param_1[0x1a] & 1;
        param_1[0x19] = 0;
        goto LAB_006b76c6;
      }
LAB_006b7b3a:
      param_1[0x1a] = param_1[0x1a] & 1;
      param_1[0x19] = 0;
LAB_006b76c6:
      if (((param_1[9] != 0) && (param_1[8] != 0)) &&
         (iVar4 = GetCurrentThreadId(), param_1[8] == iVar4)) {
        param_1[9] = param_1[9] + -1;
        return 4;
      }
      param_1[8] = 0;
      if ((char)param_1[3] != '\0') {
        LeaveCriticalSection(param_1 + 10);
        return 4;
      }
      (**(code **)(*param_1 + 0x1c))();
      return 4;
    }
    if (uVar11 == uVar10) {
      iVar4 = param_1[0x19];
    }
    else if ((param_1[0x1a] & 1U) == 0) {
      if (uVar11 * 4 < 0x100000) {
        uVar7 = 1;
        if (uVar11 != 0) {
          do {
            uVar7 = uVar7 * 2;
          } while (uVar7 <= uVar11);
        }
      }
      else {
        uVar7 = (uVar11 & 0xfffffc00) + 0x400;
      }
      if (uVar10 * 4 < 0x100000) {
        uVar8 = uVar10;
        if ((1 < uVar10) &&
           (uVar8 = 1 << ((char)((uint)(float)uVar10 >> 0x17) + 0x81U & 0x1f), uVar8 < uVar10)) {
          uVar8 = uVar8 * 2;
        }
      }
      else {
        uVar8 = (uVar10 & 0x7ffffc00) + 0x400;
      }
      iVar4 = param_1[0x19];
      if (uVar8 != uVar7) {
        if (uVar7 == 0) {
          if (iVar4 != 0) {
            func_0x0097caf0(iVar4);
            param_1[0x19] = 0;
          }
        }
        else {
          iVar4 = func_0x0097c810(iVar4,uVar7 * 4);
          param_1[0x19] = iVar4;
        }
        iVar4 = param_1[0x19];
        if (iVar4 == 0) goto LAB_006b7b3a;
      }
      param_1[0x1a] = uVar11 * 2 | param_1[0x1a] & 1U;
    }
    else {
      if (uVar11 == 0) {
        if (param_1[0x19] != 0) {
          func_0x0097caf0(param_1[0x19]);
          param_1[0x19] = 0;
        }
      }
      else {
        iVar4 = func_0x0097c810(param_1[0x19],uVar11 * 4);
        param_1[0x19] = iVar4;
      }
      iVar4 = param_1[0x19];
      if (iVar4 == 0) goto LAB_006b7b3a;
      param_1[0x1a] = uVar11 * 2 | param_1[0x1a] & 1U;
    }
    if (iVar4 == 0) goto LAB_006b76c6;
    for (; uVar10 < uVar11; uVar10 = uVar10 + 1) {
      *(undefined4 *)(param_1[0x19] + uVar10 * 4) = 0;
    }
  }
  bVar2 = false;
  if (param_2 < (uint)param_1[0x1a] >> 1) {
    uVar10 = *(uint *)(param_1[0x19] + param_2 * 4) & 0xffffff;
  }
  else {
    uVar10 = 0;
  }
  if ((uVar10 < *param_3) || (param_1[0x1e] == param_2)) {
    if ((((param_1[0x20] & 0xfffffffeU) == 0) || (0x7fffffff - *param_3 < (uint)param_1[0x1c])) &&
       (iVar4 = func_0x006b6620(), iVar4 != 0)) {
      if (((param_1[9] != 0) && (param_1[8] != 0)) &&
         (iVar5 = GetCurrentThreadId(), param_1[8] == iVar5)) {
        param_1[9] = param_1[9] + -1;
        return iVar4;
      }
      param_1[8] = 0;
      if ((char)param_1[3] != '\0') {
        LeaveCriticalSection(param_1 + 10);
        return iVar4;
      }
      (**(code **)(*param_1 + 0x1c))();
      return iVar4;
    }
    bVar2 = true;
    if ((param_1[0x1e] != param_2) || (*(int *)(param_1[0x17] + param_2 * 4) == 0)) {
      *(int *)(param_1[0x17] + param_2 * 4) = param_1[0x1c];
    }
    uVar10 = param_1[0x26];
    puVar1 = (uint *)(param_1[0x17] + param_2 * 4);
    uVar11 = *puVar1;
    if ((uVar11 < uVar10) ||
       (uVar7 = *param_3, (uint)param_1[0x29] >> 1 < (uVar11 - uVar10) + uVar7)) goto LAB_006b7d27;
    if (param_2 < (uint)param_1[0x1a] >> 1) {
      uVar11 = *(uint *)(param_1[0x19] + param_2 * 4) & 0xffffff;
    }
    else {
      uVar11 = 0;
    }
    if (uVar7 != uVar11) goto LAB_006b7d27;
    pbVar6 = (byte *)((param_1[0x28] - uVar10) + *puVar1);
    pbVar9 = (byte *)param_3[1];
    for (; 3 < uVar7; uVar7 = uVar7 - 4) {
      if (*(int *)pbVar9 != *(int *)pbVar6) goto LAB_006b7cc0;
      pbVar6 = pbVar6 + 4;
      pbVar9 = pbVar9 + 4;
    }
    if (uVar7 == 0) {
LAB_006b7d1d:
      iVar5 = 0;
    }
    else {
LAB_006b7cc0:
      iVar4 = (uint)*pbVar9 - (uint)*pbVar6;
      if (iVar4 == 0) {
        if (uVar7 == 1) goto LAB_006b7d1d;
        iVar4 = (uint)pbVar9[1] - (uint)pbVar6[1];
        if (iVar4 == 0) {
          if (uVar7 == 2) goto LAB_006b7d1d;
          iVar4 = (uint)pbVar9[2] - (uint)pbVar6[2];
          if (iVar4 == 0) {
            if ((uVar7 == 3) || (iVar4 = (uint)pbVar9[3] - (uint)pbVar6[3], iVar4 == 0))
            goto LAB_006b7d1d;
          }
        }
      }
      iVar5 = 1;
      if (iVar4 < 1) {
        iVar5 = -1;
      }
    }
    if (iVar5 != 0) goto LAB_006b7d27;
  }
  else {
LAB_006b7d27:
    uVar3 = param_4;
    *(undefined4 *)(param_1[0x15] + param_2 * 4) = param_4;
    if (*param_3 == 0) {
      if (bVar2) {
        func_0x006b7280(param_2,param_3);
      }
      *(undefined4 *)(param_1[0x17] + param_2 * 4) = 0;
      *(undefined4 *)(param_1[0x19] + param_2 * 4) = 0;
      *(undefined4 *)(param_1[0x15] + param_2 * 4) = 0;
      if (((param_1[9] != 0) && (param_1[8] != 0)) &&
         (iVar4 = GetCurrentThreadId(), param_1[8] == iVar4)) goto LAB_006b7f6f;
      param_1[8] = 0;
      if ((char)param_1[3] == '\0') {
        (**(code **)(*param_1 + 0x1c))();
        return 0;
      }
      goto LAB_006b7f8c;
    }
    if (bVar2) {
      *(uint *)(param_1[0x19] + param_2 * 4) = param_1[0x1d] << 0x18 | *param_3;
    }
    else {
      puVar1 = (uint *)(param_1[0x19] + param_2 * 4);
      *puVar1 = *puVar1 & 0xff000000;
      puVar1 = (uint *)(param_1[0x19] + param_2 * 4);
      *puVar1 = *puVar1 | *param_3;
    }
    iVar4 = func_0x006b61b0();
    if (iVar4 == 0) {
      if (((param_1[9] != 0) && (param_1[8] != 0)) &&
         (iVar4 = GetCurrentThreadId(), param_1[8] == iVar4)) {
        param_1[9] = param_1[9] + -1;
        return -1;
      }
      param_1[8] = 0;
      if ((char)param_1[3] == '\0') {
        (**(code **)(*param_1 + 0x1c))();
        return -1;
      }
      LeaveCriticalSection(param_1 + 10);
      return -1;
    }
    if (bVar2) {
      func_0x006b7280(param_2,param_3);
    }
    else if (*param_3 != 0) {
      if ((param_1[0x26] != 0xffffffff) &&
         ((uint)param_1[0x26] <= *(uint *)(param_1[0x17] + param_2 * 4))) {
        func_0x006b71b0();
      }
      param_4 = 0;
      func_0x0099de00(&param_4);
      if ((param_3 != (uint *)0x0) && (param_3 < *(uint **)(param_1[0x17] + unaff_retaddr * 4))) {
        *(undefined4 *)(param_1[0x17] + unaff_retaddr * 4) = 0;
        *(undefined4 *)(param_1[0x19] + unaff_retaddr * 4) = 0;
        *(undefined4 *)(param_1[0x15] + unaff_retaddr * 4) = 0;
        iVar4 = FUN_006b75f0(unaff_retaddr,param_2,uVar3);
LAB_006b7ee0:
        if (((param_1[9] != 0) && (param_1[8] != 0)) &&
           (iVar5 = GetCurrentThreadId(), param_1[8] == iVar5)) {
          param_1[9] = param_1[9] + -1;
          return iVar4;
        }
        param_1[8] = 0;
        if ((char)param_1[3] != '\0') {
          LeaveCriticalSection(param_1 + 10);
          return iVar4;
        }
        (**(code **)(*param_1 + 0x1c))();
        return iVar4;
      }
      func_0x0099dd50(0);
      iVar4 = func_0x0099df60();
      if (iVar4 != 0) goto LAB_006b7ee0;
    }
  }
  if (((param_1[9] != 0) && (param_1[8] != 0)) &&
     (iVar4 = GetCurrentThreadId(), param_1[8] == iVar4)) {
LAB_006b7f6f:
    param_1[9] = param_1[9] + -1;
    return 0;
  }
  param_1[8] = 0;
  if ((char)param_1[3] == '\0') {
    (**(code **)(*param_1 + 0x1c))();
    return 0;
  }
LAB_006b7f8c:
  LeaveCriticalSection(param_1 + 10);
  return 0;
}


