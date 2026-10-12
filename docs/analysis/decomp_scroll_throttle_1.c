// Address: 007301f0
// Function: FUN_007301f0
// Target requested: 0x007301F0

undefined4 __thiscall FUN_007301f0(int param_1,int *param_2,undefined4 param_3,char param_4)

{
  undefined4 *puVar1;
  uint uVar2;
  uint uVar3;
  int iVar4;
  undefined4 *puVar5;
  uint uVar6;
  int iVar7;
  
  uVar2 = *(uint *)(param_1 + 0x28c) >> 1;
  if (((uVar2 != 0) && (param_4 == '\0')) && (uVar6 = 0, uVar2 != 0)) {
    iVar7 = 0;
    do {
      iVar4 = *(int *)(param_1 + 0x288);
      puVar1 = (undefined4 *)(iVar4 + iVar7);
      if (((*(int *)(iVar4 + iVar7) < *(int *)(iVar4 + 8 + iVar7)) &&
          ((int)puVar1[1] < (int)puVar1[3])) && ((param_2[1] & 1U) == 0)) {
        uVar2 = (uint)param_2[1] >> 1;
        if (uVar2 << 4 < 0x100000) {
          uVar3 = uVar2;
          if ((uVar2 & uVar2 - 1) == 0) {
            if (uVar2 == 0) {
              uVar3 = 1;
            }
            else {
              uVar3 = uVar2 * 2;
            }
          }
        }
        else {
          uVar3 = (uVar2 & 0x7ffffc00) + 0x400;
        }
        if (uVar2 < uVar3) {
          if (uVar3 == 0) {
            if (*param_2 != 0) {
              func_0x0097caf0(*param_2);
              *param_2 = 0;
            }
          }
          else {
            iVar4 = func_0x0097c810(*param_2,uVar3 << 4);
            *param_2 = iVar4;
          }
        }
        if (*param_2 != 0) {
          puVar5 = (undefined4 *)(((uint)param_2[1] >> 1) * 0x10 + *param_2);
          *puVar5 = *puVar1;
          puVar5[1] = puVar1[1];
          puVar5[2] = puVar1[2];
          puVar5[3] = puVar1[3];
          param_2[1] = (param_2[1] & 0xfffffffeU) + 2 ^ param_2[1] & 1U;
        }
      }
      uVar6 = uVar6 + 1;
      iVar7 = iVar7 + 0x10;
    } while (uVar6 < *(uint *)(param_1 + 0x28c) >> 1);
  }
  return 0;
}


