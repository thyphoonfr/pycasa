// Address: 004156f0
// Function: FUN_004156f0
// Target requested: 0x004156F0

undefined4 FUN_004156f0(void)

{
  int in_EAX;
  undefined4 uVar1;
  
  if (*(char *)(in_EAX + 0x1c) != '\0') {
    return 0;
  }
  *(double *)(in_EAX + 0x10) = *(double *)(in_EAX + 8) + *(double *)(in_EAX + 0x10);
  uVar1 = func_0x00415610();
  return uVar1;
}


