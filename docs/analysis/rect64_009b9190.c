// Address: 009b9190
// Function: FUN_009b9190
// Target requested: 0x009b9190

undefined4 __thiscall FUN_009b9190(uint *param_1,uint param_2,uint param_3)

{
  param_1[1] = param_3 & 0xffff;
  *param_1 = param_3 >> 0x10;
  param_1[3] = param_2 & 0xffff;
  param_1[2] = param_2 >> 0x10;
  return 0;
}


