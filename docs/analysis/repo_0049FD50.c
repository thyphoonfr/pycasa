// Address: 0049fd50
// Function: FUN_0049fd50
// Target requested: 0x0049FD50

void FUN_0049fd50(int param_1)

{
  int iVar1;
  int *unaff_ESI;
  
  if (*(int *)(param_1 + 4) == 0) {
    if ((*unaff_ESI != 0) && (unaff_ESI[1] != 0)) {
      func_0x0097caf0(unaff_ESI[1]);
    }
    *unaff_ESI = 0;
    unaff_ESI[1] = 0;
    return;
  }
  iVar1 = func_0x009bd220(0);
  if (iVar1 == 0) {
    func_0x00bf2350(unaff_ESI[1],*(undefined4 *)(param_1 + 4),*unaff_ESI);
  }
  return;
}


