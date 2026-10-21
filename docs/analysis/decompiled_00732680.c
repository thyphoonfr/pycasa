// Address: 007325a0
// Function: FUN_007325a0
// Target requested: 0x00732680

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_007325a0(void)

{
  int *piVar1;
  undefined4 uVar2;
  undefined4 *unaff_ESI;
  
  if ((_DAT_00da0398 & 1) == 0) {
    _DAT_00da0398 = _DAT_00da0398 | 1;
    piVar1 = (int *)func_0x009ae560(&UNK_00cae49c);
    if (*piVar1 == 0) {
      _DAT_00d6eb28 = 0;
    }
    else {
      _DAT_00d6eb28 = *piVar1 + 4;
    }
    _DAT_00d6eb34 = 0;
    _DAT_00d6eb38 = 0;
    _DAT_00d6eb2c = 0;
    _DAT_00d6eb30 = 0;
    _DAT_00d6eb32 = 0x9d40;
    piVar1 = (int *)func_0x009ae560(&UNK_00cae478);
    if (*piVar1 == 0) {
      _DAT_00d6eb3c = 0;
    }
    else {
      _DAT_00d6eb3c = *piVar1 + 4;
    }
    _DAT_00d6eb40 = 0;
    _DAT_00d6eb44 = 0;
    _DAT_00d6eb46 = 0x9d41;
    _DAT_00d6eb48 = 0;
    _DAT_00d6eb4c = 0;
  }
  *(undefined1 *)(unaff_ESI + 1) = 1;
  uVar2 = CreatePopupMenu();
  *unaff_ESI = uVar2;
  func_0x00a6aee0(&DAT_00d6eb28,2,0);
  func_0x00a6ae90(0xa5);
  return;
}


