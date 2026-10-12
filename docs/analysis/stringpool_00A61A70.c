// Address: 00a61a70
// Function: FUN_00a61a70
// Target requested: 0x00A61A70

undefined4 __fastcall
FUN_00a61a70(undefined4 param_1,uint param_2,uint *param_3,uint *param_4,int *param_5)

{
  int iVar1;
  int iVar2;
  int *in_EAX;
  undefined4 uVar3;
  uint uVar4;
  uint *puVar5;
  
  uVar4 = *param_3;
  uVar3 = 0xffffffff;
  if ((uVar4 <= param_2) && (param_2 < *in_EAX + uVar4)) {
    *param_5 = (*param_4 * *in_EAX - uVar4) + param_2;
    return 0;
  }
  uVar4 = 0;
  if ((uint)in_EAX[3] >> 1 != 0) {
    puVar5 = (uint *)in_EAX[2];
    while ((param_2 < *puVar5 || (*in_EAX + *puVar5 <= param_2))) {
      uVar4 = uVar4 + 1;
      puVar5 = puVar5 + 1;
      if ((uint)in_EAX[3] >> 1 <= uVar4) {
        return 0xffffffff;
      }
    }
    iVar1 = *in_EAX;
    iVar2 = *(int *)(in_EAX[2] + uVar4 * 4);
    *param_3 = *(uint *)(in_EAX[2] + uVar4 * 4);
    *param_4 = uVar4;
    *param_5 = (iVar1 * uVar4 - iVar2) + param_2;
    uVar3 = 0;
  }
  return uVar3;
}


