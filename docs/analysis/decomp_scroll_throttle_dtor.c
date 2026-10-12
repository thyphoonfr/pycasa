// Address: 0072e120
// Function: FUN_0072e120
// Target requested: 0x0072E120

void __fastcall FUN_0072e120(undefined4 param_1)

{
  int unaff_ESI;
  
  if (*(int *)(unaff_ESI + 0x2b8) != 0) {
    func_0x0097caf0(*(int *)(unaff_ESI + 0x2b8),param_1);
  }
  *(uint *)(unaff_ESI + 700) = *(uint *)(unaff_ESI + 700) & 1;
  *(undefined4 *)(unaff_ESI + 0x2b8) = 0;
  if (*(int *)(unaff_ESI + 0x288) != 0) {
    func_0x0097caf0(*(int *)(unaff_ESI + 0x288),param_1);
  }
  *(uint *)(unaff_ESI + 0x28c) = *(uint *)(unaff_ESI + 0x28c) & 1;
  *(undefined4 *)(unaff_ESI + 0x288) = 0;
  func_0x009ddba0();
  return;
}


