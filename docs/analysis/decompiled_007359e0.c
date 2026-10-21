// Address: 007359e0
// Function: FUN_007359e0
// Target requested: 0x007359e0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_007359e0(void)

{
  int *piVar1;
  undefined4 uVar2;
  undefined4 *unaff_EDI;
  
  if ((_DAT_00da0350 & 1) == 0) {
    _DAT_00da0350 = _DAT_00da0350 | 1;
    piVar1 = (int *)func_0x009ae560(&UNK_00caf334);
    if (*piVar1 == 0) {
      _DAT_00d6f9a8 = 0;
    }
    else {
      _DAT_00d6f9a8 = *piVar1 + 4;
    }
    _DAT_00d6f9b4 = 0;
    _DAT_00d6f9b8 = 0;
    _DAT_00d6f9c0 = 0;
    _DAT_00d6f9c4 = 0;
    _DAT_00d6f9c8 = 0;
    _DAT_00d6f9cc = 0;
    _DAT_00d6f9ac = 0;
    _DAT_00d6f9b0 = 0;
    _DAT_00d6f9b2 = 0x9c69;
    _DAT_00d6f9bc = 0;
    piVar1 = (int *)func_0x009ae560(&UNK_00caf30c);
    if (*piVar1 == 0) {
      _DAT_00d6f9d0 = 0;
    }
    else {
      _DAT_00d6f9d0 = *piVar1 + 4;
    }
    _DAT_00d6f9dc = 0;
    _DAT_00d6f9e0 = 0;
    _DAT_00d6f9d4 = &UNK_00c8c878;
    _DAT_00d6f9d8 = 0;
    _DAT_00d6f9da = 0x9cb8;
    piVar1 = (int *)func_0x009ae560(&UNK_00caf2ec);
    if (*piVar1 == 0) {
      _DAT_00d6f9e4 = 0;
    }
    else {
      _DAT_00d6f9e4 = *piVar1 + 4;
    }
    _DAT_00d6f9f0 = 0;
    _DAT_00d6f9f4 = 0;
    _DAT_00d6f9e8 = &UNK_00c7eae0;
    _DAT_00d6f9ec = 0;
    _DAT_00d6f9ee = 0x9c90;
    piVar1 = (int *)func_0x009ae560(&UNK_00cae188);
    if (*piVar1 == 0) {
      _DAT_00d6f9f8 = 0;
    }
    else {
      _DAT_00d6f9f8 = *piVar1 + 4;
    }
    _DAT_00d6fa04 = 0;
    _DAT_00d6fa08 = 0;
    _DAT_00d6fa10 = 0;
    _DAT_00d6fa14 = 0;
    _DAT_00d6fa18 = 0;
    _DAT_00d6fa1c = 0;
    _DAT_00d6f9fc = &UNK_00c8c818;
    _DAT_00d6fa00 = 0;
    _DAT_00d6fa02 = 0x9c47;
    _DAT_00d6fa0c = 0;
    piVar1 = (int *)func_0x009ae560(&UNK_00cae414);
    if (*piVar1 == 0) {
      _DAT_00d6fa20 = 0;
    }
    else {
      _DAT_00d6fa20 = *piVar1 + 4;
    }
    _DAT_00d6fa2c = 0;
    _DAT_00d6fa30 = 0;
    _DAT_00d6fa24 = 0;
    _DAT_00d6fa28 = 0;
    _DAT_00d6fa2a = 0x9c5e;
    piVar1 = (int *)func_0x009ae560(&UNK_00cae43c);
    if (*piVar1 == 0) {
      _DAT_00d6fa34 = 0;
    }
    else {
      _DAT_00d6fa34 = *piVar1 + 4;
    }
    _DAT_00d6fa38 = 0;
    _DAT_00d6fa3c = 0;
    _DAT_00d6fa3e = 0;
    _DAT_00d6fa40 = func_0x007318a0();
    _DAT_00d6fa4c = 0;
    _DAT_00d6fa50 = 0;
    _DAT_00d6fa54 = 0;
    _DAT_00d6fa58 = 0;
    _DAT_00d6fa44 = 4;
    _DAT_00d6fa48 = 0;
    piVar1 = (int *)func_0x009ae560(&UNK_00caf2b8);
    if (*piVar1 == 0) {
      _DAT_00d6fa5c = 0;
    }
    else {
      _DAT_00d6fa5c = *piVar1 + 4;
    }
    _DAT_00d6fa60 = 0;
    _DAT_00d6fa64 = 0;
    _DAT_00d6fa66 = 0x9d44;
    _DAT_00d6fa68 = 0;
    _DAT_00d6fa6c = 0;
  }
  *(undefined1 *)(unaff_EDI + 1) = 1;
  uVar2 = CreatePopupMenu();
  *unaff_EDI = uVar2;
  func_0x00a6aee0(&DAT_00d6f9a8,10,0);
  func_0x00a6ae90(0x13c);
  return;
}


