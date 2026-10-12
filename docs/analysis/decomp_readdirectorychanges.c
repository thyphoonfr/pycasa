// Address: 00704f20
// Function: FUN_00704f20
// Target requested: 0x00704F20

/* WARNING: Removing unreachable block (ram,0x00705237) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00704f20(void)

{
  int *piVar1;
  byte *pbVar2;
  char cVar3;
  int iVar4;
  int iVar5;
  undefined4 uVar6;
  int *extraout_ECX;
  int iStack_8;
  
  func_0x00bf6b80();
  iStack_8 = -1;
  cVar3 = (**(code **)(*extraout_ECX + 4))();
  if (cVar3 == '\0') {
    while (iVar4 = (*_DAT_00d4a198)(extraout_ECX[0x34],&stack0x00000014,0x10000,1,0x57,0,
                                    &stack0x00000000,0), iVar4 != 0) {
      iVar5 = GetOverlappedResult(extraout_ECX[0x34],&stack0x00000000,&stack0xfffffffc,0);
      iVar4 = iStack_8;
      while (iVar5 == 0) {
        cVar3 = (**(code **)(*extraout_ECX + 4))();
        if (cVar3 != '\0') goto LAB_0070525a;
        if (extraout_ECX[0x17] == 0) {
          if (iVar4 != -1) goto LAB_00705003;
          uVar6 = 0xffffffff;
          iVar4 = -1;
        }
        else {
          iStack_8 = 2;
LAB_00705003:
          uVar6 = 500;
          iVar4 = iStack_8;
        }
        iVar5 = WaitForSingleObject(extraout_ECX[0x35],uVar6);
        cVar3 = (**(code **)(*extraout_ECX + 4))();
        if (cVar3 != '\0') goto LAB_0070525a;
        func_0x007072c0();
        if (iVar5 == 0x102) {
          if (iVar4 == 0) {
            iVar4 = GetCurrentThreadId();
            if ((extraout_ECX[0x24] == 0) || (extraout_ECX[0x24] != iVar4)) {
              if ((char)extraout_ECX[0x1f] == '\0') {
                (**(code **)(extraout_ECX[0x1c] + 0x18))();
              }
              else {
                EnterCriticalSection(extraout_ECX + 0x26);
              }
              extraout_ECX[0x25] = 0;
              extraout_ECX[0x24] = iVar4;
            }
            else {
              extraout_ECX[0x25] = extraout_ECX[0x25] + 1;
            }
            *(undefined1 *)(extraout_ECX + 0x31) = 1;
            if (((extraout_ECX[0x25] == 0) || (extraout_ECX[0x24] == 0)) ||
               (iVar4 = GetCurrentThreadId(), extraout_ECX[0x24] != iVar4)) {
              extraout_ECX[0x24] = 0;
              if ((char)extraout_ECX[0x1f] == '\0') {
                (**(code **)(extraout_ECX[0x1c] + 0x1c))();
              }
              else {
                LeaveCriticalSection(extraout_ECX + 0x26);
              }
            }
            else {
              extraout_ECX[0x25] = extraout_ECX[0x25] + -1;
            }
            SetEvent(*(undefined4 *)extraout_ECX[0x36]);
            SetEvent(extraout_ECX[0x13]);
          }
          else if (iVar4 != -1) {
            iStack_8 = iVar4 + -1;
          }
          pbVar2 = (byte *)extraout_ECX[0x39];
          if (pbVar2 != (byte *)0x0) {
            if (*pbVar2 < 0x80) {
              cVar3 = InterlockedDecrement(pbVar2);
              if (cVar3 == '\x7f') {
                if (*pbVar2 < 0x80) {
                  cVar3 = InterlockedIncrement(pbVar2);
                }
                else {
                  cVar3 = -1;
                }
              }
              if (cVar3 == '\0') {
                func_0x0097caf0(extraout_ECX[0x39]);
              }
            }
            extraout_ECX[0x39] = 0;
          }
          pbVar2 = (byte *)extraout_ECX[0x38];
          piVar1 = extraout_ECX + 0x38;
          if (pbVar2 != (byte *)extraout_ECX[0x39]) {
            if (pbVar2 != (byte *)0x0) {
              if (*pbVar2 < 0x80) {
                cVar3 = InterlockedDecrement(pbVar2);
                if (cVar3 == '\x7f') {
                  if (*pbVar2 < 0x80) {
                    cVar3 = InterlockedIncrement(pbVar2);
                  }
                  else {
                    cVar3 = -1;
                  }
                }
                if (cVar3 == '\0') {
                  func_0x0097caf0(*piVar1);
                }
              }
              *piVar1 = 0;
            }
            pbVar2 = (byte *)extraout_ECX[0x39];
            *piVar1 = (int)pbVar2;
            if ((pbVar2 != (byte *)0x0) &&
               ((0x7f < *pbVar2 || (cVar3 = InterlockedIncrement(pbVar2), cVar3 == -1)))) {
              func_0x00985a60();
            }
          }
        }
        iVar4 = 0;
        iVar5 = GetOverlappedResult(extraout_ECX[0x34],&stack0x00000000,&stack0xfffffffc);
      }
      cVar3 = (**(code **)(*extraout_ECX + 4))();
      if ((cVar3 != '\0') || (cVar3 = (**(code **)(*extraout_ECX + 4))(), cVar3 != '\0')) break;
    }
  }
LAB_0070525a:
  func_0x00bef10a();
  return;
}


