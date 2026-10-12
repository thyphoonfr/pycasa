// Address: 006b8640
// Function: FUN_006b8640
// Target requested: 0x006B8640

int FUN_006b8640(undefined4 param_1)

{
  int in_EAX;
  uint uVar1;
  int iVar2;
  int iVar3;
  uint uVar4;
  undefined4 uVar5;
  
  uVar4 = 0;
  if ((*(uint *)(in_EAX + 0x68) & 0xfffffffe) != 0) {
    do {
      uVar1 = (uint)*(byte *)(*(int *)(in_EAX + 100) + 3 + uVar4 * 4);
      if (((*(uint *)(in_EAX + 0x80) >> 1 <= uVar1) ||
          (*(int *)(*(int *)(in_EAX + 0x7c) + 4 + uVar1 * 0x14) == 0)) &&
         (iVar2 = FUN_006b61e0(uVar1,param_1), iVar2 != 0)) {
        if (*(int *)(in_EAX + 0x84) == 0) {
          iVar3 = 0;
        }
        else {
          iVar3 = *(int *)(in_EAX + 0x84) + 4;
        }
        uVar5 = 0x2cf;
        goto LAB_006b86e2;
      }
      uVar4 = uVar4 + 1;
    } while (uVar4 < *(uint *)(in_EAX + 0x68) >> 1);
  }
  if (((*(uint *)(in_EAX + 0x80) & 0xfffffffe) != 0) ||
     (iVar2 = FUN_006b61e0(0,param_1), iVar2 == 0)) {
    return 0;
  }
  if (*(int *)(in_EAX + 0x84) == 0) {
    iVar3 = 0;
    uVar5 = 0x2d8;
  }
  else {
    iVar3 = *(int *)(in_EAX + 0x84) + 4;
    uVar5 = 0x2d8;
  }
LAB_006b86e2:
  func_0x0099cde0(iVar2,iVar3,&UNK_00ca847c,uVar5);
  return iVar2;
}


