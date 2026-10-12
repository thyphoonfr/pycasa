// Address: 005c2100
// Function: FUN_005c2100
// Target requested: 0x005C2100

void FUN_005c2100(void)

{
  byte *pbVar1;
  char cVar2;
  int *in_EAX;
  int *unaff_ESI;
  
  if (*in_EAX != *unaff_ESI) {
    func_0x00401000();
    pbVar1 = (byte *)*unaff_ESI;
    *in_EAX = (int)pbVar1;
    if (pbVar1 != (byte *)0x0) {
      if ((*pbVar1 < 0x80) && (cVar2 = InterlockedIncrement(pbVar1), cVar2 != -1)) {
        return;
      }
      func_0x00985a60();
    }
  }
  return;
}


