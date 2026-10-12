// Address: 00a61700
// Function: FUN_00a61700
// Target requested: 0x00A61700

undefined4 FUN_00a61700(uint param_1)

{
  int *piVar1;
  int iVar2;
  int iVar3;
  undefined4 *unaff_ESI;
  uint uVar4;
  
  iVar2 = param_1;
  piVar1 = (int *)(param_1 + 4);
  if ((((*piVar1 == 0) ||
       (param_1 = (uint)unaff_ESI[3] >> 1, iVar3 = func_0x00c07a30(&param_1,4,1,*piVar1), iVar3 != 1
       )) || (*(int *)(iVar2 + 4) == 0)) ||
     (((iVar3 = func_0x00c07a30(), iVar3 != 1 || (*(int *)(iVar2 + 4) == 0)) ||
      (iVar3 = func_0x00c07a30(unaff_ESI + 1,4,1,*(int *)(iVar2 + 4)), iVar3 != 1)))) {
    return 2;
  }
  uVar4 = 0;
  if (param_1 != 0) {
    do {
      if (*(int *)(iVar2 + 4) == 0) {
        return 2;
      }
      iVar3 = func_0x00c07a30(*(undefined4 *)(unaff_ESI[2] + uVar4 * 4),*unaff_ESI,1,
                              *(int *)(iVar2 + 4));
      if (iVar3 != 1) {
        return 2;
      }
      uVar4 = uVar4 + 1;
    } while (uVar4 < param_1);
  }
  return 0;
}


