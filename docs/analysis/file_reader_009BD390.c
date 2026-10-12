// Address: 009bd390
// Function: FUN_009bd390
// Target requested: 0x009BD390

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 * FUN_009bd390(undefined4 *param_1,undefined4 param_2)

{
  char cVar1;
  int *piVar2;
  int iVar3;
  undefined4 uVar4;
  float10 fVar5;
  
  *param_1 = 0;
  piVar2 = (int *)func_0x00408b50();
  param_1[1] = 0;
  param_1[2] = 0;
  param_1[3] = 0;
  param_1[4] = 0;
  if (*piVar2 == 0) {
    iVar3 = 0;
  }
  else {
    iVar3 = *piVar2 + 4;
  }
  uVar4 = func_0x0099db60(iVar3);
  param_1[5] = uVar4;
  func_0x00408c00();
  if ((param_1[5] != 0) && (param_1[5] != 10)) {
    QueryPerformanceCounter(&stack0xfffff5cc);
    cVar1 = func_0x00992ed0();
    if (cVar1 != '\0') {
      do {
        fVar5 = (float10)func_0x009a51b0(&stack0xfffff5cc);
        if ((float10)_DAT_00c7d9d0 < fVar5) {
          return param_1;
        }
        iVar3 = WaitForSingleObject(_DAT_00d689cc,500);
        if ((iVar3 != 0x80) && (iVar3 == 0)) {
          return param_1;
        }
        func_0x0099db60(param_2);
      } while ((param_1[5] != 0) && (param_1[5] != 10));
    }
  }
  func_0x009bd490(param_1);
  return param_1;
}


