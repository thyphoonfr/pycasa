// Address: 009b91c0
// Function: FUN_009b91c0
// Target requested: 0x009b91c0

undefined4 __thiscall FUN_009b91c0(undefined4 param_1,char param_2)

{
  int *in_EAX;
  undefined4 uVar1;
  uint uVar2;
  
  uVar2 = *in_EAX << 0x10 | (uint)*(ushort *)(in_EAX + 1);
  uVar1 = CONCAT22((short)in_EAX[2],(short)in_EAX[3]);
  if (param_2 != '\0') {
    func_0x00c08243(param_1,&UNK_00cd9554,uVar1,uVar2);
    return 0;
  }
  func_0x00c08243(param_1,&UNK_00c82fcc,uVar1,uVar2);
  return 0;
}


