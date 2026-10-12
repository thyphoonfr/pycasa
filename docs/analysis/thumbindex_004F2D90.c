// Address: 004f2d90
// Function: FUN_004f2d90
// Target requested: 0x004F2D90

/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_004f2d90(int param_1)

{
  char cVar1;
  char *pcVar2;
  int iVar3;
  char *pcVar4;
  int in_stack_00000a2c;
  
  func_0x00bf6b80();
  func_0x00408b50();
  func_0x00980ec0(0);
  func_0x009a37b0();
  cVar1 = func_0x00992ed0();
  if (cVar1 == '\0') {
    func_0x009a37b0();
    cVar1 = func_0x00992ed0();
    if (cVar1 != '\0') {
      func_0x00408b50();
      func_0x00980ec0(0);
      func_0x009a37b0();
      if (in_stack_00000a2c == 0) {
        pcVar4 = (char *)0x0;
      }
      else {
        pcVar4 = (char *)(in_stack_00000a2c + 4);
      }
      if ((((param_1 != 0) && (pcVar2 = (char *)(param_1 + 4), pcVar2 != (char *)0x0)) &&
          (*pcVar2 != '\0')) &&
         (((pcVar4 != (char *)0x0 && (*pcVar4 != '\0')) &&
          (iVar3 = (*_DAT_00d694d4)(pcVar2,pcVar4), iVar3 == 0)))) {
        GetLastError();
        func_0x00991330();
      }
      func_0x00408c00();
      func_0x00408c00();
      func_0x00bef10a();
      return;
    }
  }
  func_0x00408c00();
  func_0x00bef10a();
  return;
}


