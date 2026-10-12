// Address: 0099c1e0
// Function: FUN_0099c1e0
// Target requested: 0x0099C1E0

undefined4 FUN_0099c1e0(undefined4 param_1)

{
  undefined4 *in_EAX;
  int iVar1;
  uint uVar2;
  uint uVar3;
  uint uStack_4;
  
  uVar3 = (uint)in_EAX[1] >> 1;
  uStack_4 = uVar3;
  iVar1 = func_0x00c07a30(&uStack_4,4,1,param_1);
  if (iVar1 != 1) {
    return 2;
  }
  if (((uVar3 != 0) && ((in_EAX[1] & 0xfffffffe) != 0)) &&
     (uVar2 = func_0x00c07a30(*in_EAX,4,uVar3,param_1), uVar2 != uVar3)) {
    return 2;
  }
  return 0;
}


