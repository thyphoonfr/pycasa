// Address: 00734bc0
// Function: FUN_00734bc0
// Target requested: 0x00734ec0

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_00734bc0(void)

{
  int *piVar1;
  undefined4 uVar2;
  undefined4 *unaff_EDI;
  
  if ((_DAT_00da035c & 1) == 0) {
    _DAT_00da035c = _DAT_00da035c | 1;
    piVar1 = (int *)func_0x009ae560(&UNK_00caf094);
    if (*piVar1 == 0) {
      _DAT_00d6f5c0 = 0;
    }
    else {
      _DAT_00d6f5c0 = *piVar1 + 4;
    }
    _DAT_00d6f5cc = 0;
    _DAT_00d6f5d0 = 0;
    _DAT_00d6f5d8 = 0;
    _DAT_00d6f5dc = 0;
    _DAT_00d6f5e0 = 0;
    _DAT_00d6f5e4 = 0;
    _DAT_00d6f5c4 = 0;
    _DAT_00d6f5c8 = 0;
    _DAT_00d6f5ca = 0x9dfc;
    _DAT_00d6f5d4 = 0;
    piVar1 = (int *)func_0x009ae560(&UNK_00caf07c);
    if (*piVar1 == 0) {
      _DAT_00d6f5e8 = 0;
    }
    else {
      _DAT_00d6f5e8 = *piVar1 + 4;
    }
    _DAT_00d6f5f4 = 0;
    _DAT_00d6f5f8 = 0;
    _DAT_00d6f5ec = 0;
    _DAT_00d6f5f0 = 0;
    _DAT_00d6f5f2 = 0x9e14;
    piVar1 = (int *)func_0x009ae560(&UNK_00caead0);
    if (*piVar1 == 0) {
      _DAT_00d6f5fc = 0;
    }
    else {
      _DAT_00d6f5fc = *piVar1 + 4;
    }
    _DAT_00d6f608 = 0;
    _DAT_00d6f60c = 0;
    _DAT_00d6f614 = 0;
    _DAT_00d6f618 = 0;
    _DAT_00d6f61c = 0;
    _DAT_00d6f620 = 0;
    _DAT_00d6f600 = 0;
    _DAT_00d6f604 = 0;
    _DAT_00d6f606 = 0x9dfe;
    _DAT_00d6f610 = 0;
    piVar1 = (int *)func_0x009ae560(&UNK_00caeaa4);
    if (*piVar1 == 0) {
      _DAT_00d6f624 = 0;
    }
    else {
      _DAT_00d6f624 = *piVar1 + 4;
    }
    _DAT_00d6f630 = 0;
    _DAT_00d6f634 = 0;
    _DAT_00d6f63c = 0;
    _DAT_00d6f640 = 0;
    _DAT_00d6f644 = 0;
    _DAT_00d6f648 = 0;
    _DAT_00d6f628 = 0;
    _DAT_00d6f62c = 0;
    _DAT_00d6f62e = 0x9e0d;
    _DAT_00d6f638 = 0;
    piVar1 = (int *)func_0x009ae560(&UNK_00caf05c);
    if (*piVar1 == 0) {
      _DAT_00d6f64c = 0;
    }
    else {
      _DAT_00d6f64c = *piVar1 + 4;
    }
    _DAT_00d6f658 = 0;
    _DAT_00d6f65c = 0;
    _DAT_00d6f650 = 0;
    _DAT_00d6f654 = 0;
    _DAT_00d6f656 = 0x9e03;
    piVar1 = (int *)func_0x009ae560(&UNK_00caf040);
    if (*piVar1 == 0) {
      _DAT_00d6f660 = 0;
    }
    else {
      _DAT_00d6f660 = *piVar1 + 4;
    }
    _DAT_00d6f66c = 0;
    _DAT_00d6f670 = 0;
    _DAT_00d6f664 = 0;
    _DAT_00d6f668 = 0;
    _DAT_00d6f66a = 0x9e08;
    piVar1 = (int *)func_0x009ae560(&UNK_00caf018);
    if (*piVar1 == 0) {
      _DAT_00d6f674 = 0;
    }
    else {
      _DAT_00d6f674 = *piVar1 + 4;
    }
    _DAT_00d6f680 = 0;
    _DAT_00d6f684 = 0;
    _DAT_00d6f68c = 0;
    _DAT_00d6f690 = 0;
    _DAT_00d6f694 = 0;
    _DAT_00d6f698 = 0;
    _DAT_00d6f678 = 0;
    _DAT_00d6f67c = 0;
    _DAT_00d6f67e = 0x9e04;
    _DAT_00d6f688 = 0;
    piVar1 = (int *)func_0x009ae560(&UNK_00caefdc);
    if (*piVar1 == 0) {
      _DAT_00d6f69c = 0;
    }
    else {
      _DAT_00d6f69c = *piVar1 + 4;
    }
    _DAT_00d6f6a0 = 0;
    _DAT_00d6f6a4 = 0;
    _DAT_00d6f6a6 = 0x9e06;
    _DAT_00d6f6a8 = 0;
    _DAT_00d6f6ac = 0;
  }
  *(undefined1 *)(unaff_EDI + 1) = 1;
  uVar2 = CreatePopupMenu();
  *unaff_EDI = uVar2;
  func_0x00a6aee0(&DAT_00d6f5c0,0xc,0);
  func_0x00a6ae90(0x13a);
  return;
}


