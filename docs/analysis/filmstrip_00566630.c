// Address: 00566630
// Function: FUN_00566630
// Target requested: 0x00566630

undefined4 FUN_00566630(char param_1)

{
  int iVar1;
  int *piVar2;
  undefined4 uVar3;
  
  piVar2 = (int *)func_0x009cd080();
  if (piVar2 == (int *)0x0) {
    return 0xffffffff;
  }
  iVar1 = *piVar2;
  if (param_1 != '\0') {
    uVar3 = func_0x009ae560(&UNK_00c8e878);
    (**(code **)(iVar1 + 0x14))(uVar3);
    return 0;
  }
  uVar3 = func_0x009ae560(&UNK_00c8e8a4);
  (**(code **)(iVar1 + 0x14))(uVar3);
  return 0;
}


