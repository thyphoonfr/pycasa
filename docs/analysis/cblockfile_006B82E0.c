// Address: 006b82e0
// Function: FUN_006b82e0
// Target requested: 0x006B82E0

/* WARNING: Heritage AFTER dead removal. Example location: s0xfffffffc : 0x006b84fd */
/* WARNING: Removing unreachable block (ram,0x006b8367) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */
/* WARNING: Restarted to delay deadcode elimination for space: stack */

void FUN_006b82e0(void)

{
  char cVar1;
  int iVar2;
  
  func_0x00bf6b80();
  func_0x00991440();
  func_0x00985ff0();
  func_0x006b5bc0();
  func_0x00401000();
  func_0x00991440();
  cVar1 = func_0x00992ed0();
  if ((cVar1 == '\0') && (cVar1 = func_0x00992ed0(), cVar1 == '\0')) {
    func_0x00985ff0();
    func_0x005c2100();
    func_0x00401000();
    func_0x00985af0();
    func_0x00991440();
    cVar1 = func_0x00992ed0();
    if (cVar1 != '\0') {
      func_0x004089e0();
      iVar2 = (*_DAT_00d69520)();
      if (iVar2 == -1) {
        iVar2 = 0;
        GetLastError();
        func_0x0099cd30();
        func_0x0099cde0();
      }
      func_0x00408c00();
      if (iVar2 != 0) {
        func_0x0099dd50();
        func_0x0099df20();
      }
      func_0x0099db30();
      func_0x00991440();
      iVar2 = func_0x00994400();
      if (iVar2 == 0) {
        iVar2 = func_0x00994400();
        func_0x00408c00();
        if (iVar2 == 0) goto LAB_006b85e1;
      }
      else {
        func_0x00408c00();
      }
      func_0x00408c00();
      func_0x00401000();
      func_0x00408c00();
      func_0x00401000();
      func_0x00408c00();
      goto LAB_006b8619;
    }
LAB_006b85e1:
    func_0x00408c00();
    func_0x00401000();
  }
  func_0x00408c00();
  func_0x00401000();
  func_0x00408c00();
LAB_006b8619:
  func_0x00bef10a();
  return;
}


