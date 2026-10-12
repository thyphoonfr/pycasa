// Address: 006b9470
// Function: FUN_006b9470
// Target requested: 0x006B9470

/* WARNING: Removing unreachable block (ram,0x006b954f) */
/* WARNING: Removing unreachable block (ram,0x006b9558) */
/* WARNING: Removing unreachable block (ram,0x006b955e) */
/* WARNING: Removing unreachable block (ram,0x006b978f) */
/* WARNING: Removing unreachable block (ram,0x006b9795) */
/* WARNING: Removing unreachable block (ram,0x006b979d) */
/* WARNING: Removing unreachable block (ram,0x006b97a6) */
/* WARNING: Removing unreachable block (ram,0x006b97bc) */
/* WARNING: Removing unreachable block (ram,0x006b97c1) */
/* WARNING: Removing unreachable block (ram,0x006b97cc) */
/* WARNING: Removing unreachable block (ram,0x006b97df) */
/* WARNING: Removing unreachable block (ram,0x006b97e7) */
/* WARNING: Removing unreachable block (ram,0x006b9800) */
/* WARNING: Removing unreachable block (ram,0x006b957e) */
/* WARNING: Removing unreachable block (ram,0x006b9586) */

undefined4 FUN_006b9470(char *param_1)

{
  uint uVar1;
  undefined4 *puVar2;
  int *in_EAX;
  int iVar3;
  int iVar4;
  uint uVar5;
  int iVar6;
  undefined4 *puVar7;
  int *unaff_retaddr;
  undefined4 uStack_4;
  
  iVar3 = GetCurrentThreadId();
  iVar4 = 0;
  if ((in_EAX[8] == 0) || (in_EAX[8] != iVar3)) {
    if ((char)in_EAX[3] == '\0') {
      (**(code **)(*in_EAX + 0x18))();
    }
    else {
      EnterCriticalSection(in_EAX + 10);
    }
    in_EAX[9] = 0;
    in_EAX[8] = iVar3;
  }
  else {
    in_EAX[9] = in_EAX[9] + 1;
  }
  if (in_EAX[0x22] == 0) {
    iVar3 = 0;
  }
  else {
    iVar3 = in_EAX[0x22] + 4;
  }
  FUN_006b5d40(iVar3);
  FUN_006b91f0(unaff_retaddr);
  uVar5 = 0;
  if ((unaff_retaddr[1] & 0xfffffffeU) != 0) {
    do {
      if ((param_1 != (char *)0x0) && (*param_1 != '\0')) {
        FUN_006b5e00();
        if ((in_EAX[9] != 0) &&
           ((in_EAX[8] != 0 && (iVar3 = GetCurrentThreadId(), in_EAX[8] == iVar3)))) {
          in_EAX[9] = in_EAX[9] + -1;
          return 0xf4242;
        }
        in_EAX[8] = 0;
        if ((char)in_EAX[3] != '\0') {
          LeaveCriticalSection(in_EAX + 10);
          return 0xf4242;
        }
        (**(code **)(*in_EAX + 0x1c))();
        return 0xf4242;
      }
      uVar1 = *(uint *)(*unaff_retaddr + uVar5 * 4);
      if ((uVar1 < (uint)in_EAX[0x1a] >> 1) &&
         ((*(uint *)(in_EAX[0x19] + uVar1 * 4) & 0xffffff) != 0)) {
        func_0x006b6a50(uVar1,&stack0xffffff3c,0);
      }
      uVar5 = uVar5 + 1;
    } while (uVar5 < (uint)unaff_retaddr[1] >> 1);
  }
  func_0x006b7fc0(uStack_4,0);
  uVar5 = 0;
  *(undefined1 *)(in_EAX + 0x2a) = 0;
  if ((in_EAX[0x20] & 0xfffffffeU) != 0) {
    do {
      iVar3 = *(int *)(in_EAX[0x1f] + 0xc + iVar4);
      iVar6 = in_EAX[0x1f] + iVar4;
      if (iVar3 != 0) {
        UnmapViewOfFile(iVar3);
      }
      *(undefined4 *)(iVar6 + 0xc) = 0;
      if (*(int *)(iVar6 + 8) != 0) {
        CloseHandle(*(int *)(iVar6 + 8));
      }
      *(undefined4 *)(iVar6 + 8) = 0;
      if (*(int *)(iVar6 + 4) != 0) {
        CloseHandle(*(int *)(iVar6 + 4));
      }
      *(undefined4 *)(iVar6 + 4) = 0;
      *(undefined4 *)(iVar6 + 0x10) = 0xffffffff;
      uVar5 = uVar5 + 1;
      iVar4 = iVar4 + 0x14;
    } while (uVar5 < (uint)in_EAX[0x20] >> 1);
  }
  iVar3 = in_EAX[0x1f];
  if (iVar3 != 0) {
    iVar4 = *(int *)(iVar3 + -4);
    puVar7 = (undefined4 *)(iVar3 + iVar4 * 0x14);
joined_r0x006b9653:
    puVar2 = puVar7;
    iVar4 = iVar4 + -1;
    if (-1 < iVar4) {
      puVar7 = puVar2 + -5;
      if (puVar2[-5] != 0) goto code_r0x006b965f;
      goto LAB_006b9677;
    }
    func_0x0097caf0(iVar3 + -4);
  }
  in_EAX[0x20] = in_EAX[0x20] & 1;
  in_EAX[0x1f] = 0;
  in_EAX[0x13] = in_EAX[0x13] + 1;
  *(undefined1 *)(in_EAX + 0x14) = 1;
  FUN_006b5e00();
  if (((in_EAX[9] != 0) && (in_EAX[8] != 0)) && (iVar3 = GetCurrentThreadId(), in_EAX[8] == iVar3))
  {
    in_EAX[9] = in_EAX[9] + -1;
    return 0;
  }
  in_EAX[8] = 0;
  if ((char)in_EAX[3] != '\0') {
    LeaveCriticalSection(in_EAX + 10);
    return 0;
  }
  (**(code **)(*in_EAX + 0x1c))();
  return 0;
code_r0x006b965f:
  iVar6 = InterlockedDecrement(puVar2[-5]);
  if (iVar6 == 0) {
    func_0x0097caf0(*puVar7);
    *puVar7 = 0;
LAB_006b9677:
    if (puVar2[-2] != 0) {
      UnmapViewOfFile(puVar2[-2]);
    }
    puVar2[-2] = 0;
    if (puVar2[-3] != 0) {
      CloseHandle(puVar2[-3]);
    }
    puVar2[-3] = 0;
    if (puVar2[-4] != 0) {
      CloseHandle(puVar2[-4]);
    }
    puVar2[-4] = 0;
    puVar2[-1] = 0xffffffff;
  }
  goto joined_r0x006b9653;
}


