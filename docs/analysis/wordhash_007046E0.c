// Address: 007046e0
// Function: FUN_007046e0
// Target requested: 0x007046E0

int FUN_007046e0(int param_1,uint *param_2,int *param_3)

{
  uint uVar1;
  int iVar2;
  int *piVar3;
  int *piVar4;
  uint uStack_28;
  int iStack_24;
  undefined1 auStack_20 [4];
  uint uStack_1c;
  int iStack_18;
  int aiStack_14 [5];
  
  uStack_1c = 0;
  iStack_24 = 0;
  iVar2 = func_0x00c08d3e(&iStack_24,4,1,*(undefined4 *)(param_1 + 4));
  if (iVar2 != 1) {
    return -1;
  }
  *param_3 = iStack_24;
  iVar2 = func_0x00a617b0(param_1);
  if (iVar2 == 0) {
    uStack_28 = 0;
    iVar2 = func_0x00c08d3e(&uStack_28,4,1,*(undefined4 *)(param_1 + 4));
    if (iVar2 != 1) {
      return -1;
    }
    uStack_1c = 0;
    if (uStack_28 != 0) {
      do {
        iStack_24 = 0;
        iVar2 = func_0x00c08d3e(&iStack_24,4,1,*(undefined4 *)(param_1 + 4));
        if (iVar2 != 1) {
          return -1;
        }
        iVar2 = func_0x00a61b00(auStack_20);
        if (iVar2 != 0) {
          return iVar2;
        }
        if (iStack_24 == 0) {
          return 4;
        }
        aiStack_14[0] = iStack_24;
        uStack_1c = 0;
        iStack_18 = 0;
        aiStack_14[1] = 0;
        aiStack_14[2] = 0;
        func_0x00891110(&uStack_1c);
        if (param_2[3] == 0) {
          func_0x004de020();
        }
        if ((*param_2 < param_2[1] >> 1) || (iVar2 = func_0x004de0b0(), iVar2 == 0)) {
          iVar2 = func_0x004de1a0(param_2[1]);
          piVar4 = (int *)param_2[2];
          piVar3 = (int *)piVar4[4];
          if (piVar3 == (int *)0x0) {
            uVar1 = piVar4[1];
            if (uVar1 < (uint)piVar4[6]) {
              piVar4[3] = piVar4[3] + 1;
              piVar3 = (int *)(*piVar4 + uVar1);
              piVar4[1] = piVar4[5] + uVar1;
            }
            else {
              piVar3 = (int *)func_0x00409ce0();
            }
          }
          else {
            piVar4[3] = piVar4[3] + 1;
            piVar4[4] = *piVar3;
          }
          if (piVar3 == (int *)0x0) {
            piVar4 = (int *)0x0;
            param_1 = aiStack_14[3];
          }
          else {
            *piVar3 = 0;
            piVar4 = piVar3 + 1;
            *piVar4 = iStack_18;
            piVar3[2] = 0;
            piVar3[3] = 0;
            func_0x00891110(aiStack_14);
            *param_2 = *param_2 + 1;
            *piVar3 = *(int *)(param_2[3] + iVar2 * 4);
            *(int **)(param_2[3] + iVar2 * 4) = piVar3;
            param_1 = aiStack_14[3];
          }
        }
        else {
          piVar4 = (int *)0x0;
        }
        if (aiStack_14[0] != 0) {
          func_0x0097caf0(aiStack_14[0]);
        }
        aiStack_14[0] = 0;
        func_0x00407610();
        if (piVar4 == (int *)0x0) {
          return 4;
        }
        iVar2 = func_0x0099c240(*(undefined4 *)(param_1 + 4));
        if (iVar2 != 0) {
          return iVar2;
        }
        uStack_1c = uStack_1c + 1;
      } while (uStack_1c < uStack_28);
    }
    iVar2 = 0;
  }
  return iVar2;
}


