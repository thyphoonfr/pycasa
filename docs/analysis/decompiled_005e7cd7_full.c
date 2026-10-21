// Address: 005e7c20
// Function: FUN_005e7c20
// Target requested: 0x005e7cd7

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined4 FUN_005e7c20(undefined4 *param_1,int *param_2)

{
  int iVar1;
  undefined4 uVar2;
  int *unaff_ESI;
  undefined4 unaff_EDI;
  undefined4 uVar3;
  undefined1 auStack_28 [8];
  undefined4 uStack_20;
  undefined4 uStack_1c;
  undefined4 uStack_18;
  undefined4 uStack_14;
  undefined4 uStack_10;
  undefined4 uStack_c;
  undefined4 uStack_8;
  
  iVar1 = (**(code **)(*unaff_ESI + 0x24))();
  if (iVar1 != 0) {
    iVar1 = (**(code **)(*unaff_ESI + 0x24))();
    ClientToScreen(*(undefined4 *)(iVar1 + 0x6c),auStack_28);
  }
  uStack_18 = 0;
  uStack_14 = 0;
  uStack_10 = 0;
  uStack_c = 0;
  uStack_8 = 0;
  uStack_20 = 0x1c;
  uStack_1c = 8;
  GetMenuInfo(*param_1,&uStack_20);
  uVar3 = 1;
  iVar1 = func_0x0056c5a0();
  if (iVar1 == 0xf4242) {
    return 0xf4242;
  }
  uVar2 = 2;
  if (param_2 != (int *)0x0) {
    uVar2 = 0x102;
  }
  iVar1 = TrackPopupMenu(*param_1,uVar2,uVar3,unaff_EDI,0,_DAT_00d67850,0);
  func_0x00a6b060();
  if (param_2 != (int *)0x0) {
    *param_2 = iVar1;
  }
  *(bool *)(unaff_ESI + 0xc45) = iVar1 != 0;
  return 1000000;
}


